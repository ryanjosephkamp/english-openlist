"""
The adjudication app's replay logic — the only source of state, so the part
that must be correct before a single real verdict is cast in it.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.adjudicate.app import replay  # noqa: E402


def lines(*records):
    return [json.dumps(r) for r in records]


class TestReplay:
    def test_empty_log_is_empty_state(self):
        state = replay([])
        assert state["verdicts"] == {}
        assert state["searched"] == {}

    def test_verdict_is_recorded(self):
        state = replay(lines(
            {"event": "verdict", "item_id": "a", "verdict": "yes"}))
        assert state["verdicts"]["a"]["verdict"] == "yes"

    def test_amend_replaces_the_verdict(self):
        state = replay(lines(
            {"event": "verdict", "item_id": "a", "verdict": "yes"},
            {"event": "verdict_amend", "item_id": "a", "verdict": "no"}))
        assert state["verdicts"]["a"]["verdict"] == "no"

    def test_last_amend_wins(self):
        state = replay(lines(
            {"event": "verdict", "item_id": "a", "verdict": "yes"},
            {"event": "verdict_amend", "item_id": "a", "verdict": "no"},
            {"event": "verdict_amend", "item_id": "a", "verdict": "unsure"}))
        assert state["verdicts"]["a"]["verdict"] == "unsure"

    def test_search_events_accumulate_in_order(self):
        state = replay(lines(
            {"event": "search", "item_id": "a", "instrument": "books"},
            {"event": "search", "item_id": "a", "instrument": "scholar"},
            {"event": "search", "item_id": "b", "instrument": "web"}))
        assert state["searched"]["a"] == ["books", "scholar"]
        assert state["searched"]["b"] == ["web"]

    def test_searches_do_not_create_verdicts(self):
        state = replay(lines(
            {"event": "search", "item_id": "a", "instrument": "books"}))
        assert "a" not in state["verdicts"]

    def test_session_start_lines_are_ignored(self):
        state = replay(lines(
            {"event": "session_start", "deck": "x", "deck_size": 3}))
        assert state["verdicts"] == {} and state["searched"] == {}

    def test_blank_lines_are_tolerated(self):
        # a crash can leave a trailing newline; replay must not choke on it
        state = replay(["", "\n",
                        json.dumps({"event": "verdict", "item_id": "a",
                                    "verdict": "yes"}), "   "])
        assert state["verdicts"]["a"]["verdict"] == "yes"

    def test_multi_session_resume_never_repeats(self):
        """The resume property itself: items with verdicts anywhere in any
        session's log are done, regardless of order or interleaving."""
        session1 = lines(
            {"event": "verdict", "item_id": "a", "verdict": "yes"},
            {"event": "verdict", "item_id": "b", "verdict": "no"})
        session2 = lines(
            {"event": "verdict", "item_id": "c", "verdict": "unsure"})
        state = replay(session1 + session2)
        deck = [{"id": i} for i in ("a", "b", "c", "d", "e")]
        remaining = [d["id"] for d in deck if d["id"] not in state["verdicts"]]
        assert remaining == ["d", "e"]

    def test_searched_flag_derivation(self):
        """'Searching is never skipped' is observed, not self-reported: the
        verdict record carries what the events show."""
        state = replay(lines(
            {"event": "search", "item_id": "a", "instrument": "books"},
            {"event": "verdict", "item_id": "a", "verdict": "yes",
             "searched": True, "instruments": ["books"]},
            {"event": "verdict", "item_id": "b", "verdict": "no",
             "searched": False, "instruments": []}))
        assert state["verdicts"]["a"]["searched"] is True
        assert state["verdicts"]["b"]["searched"] is False
