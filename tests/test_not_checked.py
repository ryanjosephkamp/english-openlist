"""
Tests for "not checked tonight", and for steps that fail when they fail.

A 403 or a 429 is an answer about our access, not about the word. The Free
Dictionary API answered every one of its 994 lookups with 403 on 2026-10-25,
and each of those words was recorded as checked and still invalid. These tests
hold four things in place:

  1. A source that answers 403 or 429 is not asked again in the same run.
  2. When Collegiate does not answer, the word is not checked: it is neither
     promoted nor dated in validation_progress.json, so a later night takes it.
  3. When only a fallback fails, Collegiate's "not found" stands, the outcome
     the pipeline has always reached there.
  4. The scripts exit nonzero when their work fails, so the step goes red.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.validate_invalid_list as validate_module  # noqa: E402
from scripts.dictionary_api import (  # noqa: E402
    REFUSAL_STATUSES,
    DictionaryAPIClient,
    WordLookupResult,
    WordStatus,
)
from scripts.run_weekly_update import exit_code as update_exit_code  # noqa: E402
from scripts.validate_invalid_list import InvalidListValidator, exit_code  # noqa: E402


class FakeSource:
    """A dictionary that answers from a table and counts what it was asked."""

    def __init__(self, answers: dict, default=WordStatus.NOT_FOUND, http_status=None):
        self.answers = answers
        self.default = default
        self.http_status = http_status
        self.asked: list[str] = []
        self.is_configured = True

    async def lookup_word(self, word: str) -> WordLookupResult:
        self.asked.append(word)
        status, http_status = self.answers.get(word, (self.default, self.http_status))
        return WordLookupResult(word=word, status=status, http_status=http_status)


def refused(status: int):
    return (WordStatus.ERROR, status)


def client(collegiate: FakeSource, medical: FakeSource = None, free: FakeSource = None):
    c = DictionaryAPIClient.__new__(DictionaryAPIClient)
    c.mw = collegiate
    c.mw_medical = medical or FakeSource({})
    c.free_dict = free or FakeSource({})
    c.refused = {}
    return c


def run(coro):
    return asyncio.run(coro)


# ------------------------------------------------ 1. a refusal ends the asking

def test_the_refusal_statuses_are_403_and_429():
    assert REFUSAL_STATUSES == {403, 429}


@pytest.mark.parametrize("status", [403, 429])
def test_a_refusing_fallback_is_asked_once(status):
    free = FakeSource({}, default=WordStatus.ERROR, http_status=status)
    c = client(FakeSource({}), free=free)

    for word in ("steamship", "horrid", "initial"):
        run(c.lookup_word(word))

    assert free.asked == ["steamship"]
    assert c.refused == {"free": status}


def test_an_ordinary_error_is_not_a_refusal():
    free = FakeSource({}, default=WordStatus.ERROR, http_status=None)
    c = client(FakeSource({}), free=free)

    run(c.lookup_word("steamship"))
    run(c.lookup_word("horrid"))

    assert free.asked == ["steamship", "horrid"]
    assert c.refused == {}


# ----------------------------------------- 2. no ruling from Collegiate, no date

@pytest.mark.parametrize("status", [403, 429])
def test_a_refusing_collegiate_leaves_the_word_unchecked(status):
    collegiate = FakeSource({"steamship": refused(status)})
    c = client(collegiate)

    first = run(c.lookup_word("steamship"))
    second = run(c.lookup_word("horrid"))

    assert first.checked is False and first.http_status == status
    assert second.checked is False and second.http_status == status
    assert collegiate.asked == ["steamship"]


# ------------------------------------------- 3. a failed fallback is not a veto

def test_a_failed_fallback_keeps_collegiates_not_found():
    c = client(FakeSource({}), free=FakeSource({}, default=WordStatus.ERROR, http_status=403))
    result = run(c.lookup_word("steamship"))
    assert result.status == WordStatus.NOT_FOUND
    assert result.checked is True


def test_a_fallback_can_still_promote():
    c = client(FakeSource({}), free=FakeSource({"horrid": (WordStatus.VALID, None)}))
    assert run(c.lookup_word("horrid")).status == WordStatus.VALID


def test_medical_can_still_promote_after_free_refused():
    medical = FakeSource({"initial": (WordStatus.VALID, None)})
    free = FakeSource({}, default=WordStatus.ERROR, http_status=403)
    c = client(FakeSource({}), medical=medical, free=free)

    run(c.lookup_word("steamship"))
    assert run(c.lookup_word("initial")).status == WordStatus.VALID


# ------------------------------------- the validator: dates only what it checked

@pytest.fixture
def night(tmp_path, monkeypatch):
    """A validator over a 4-word invalid list in tmp_path, with fake sources."""
    words = ["steamship", "horrid", "initial", "rallying"]
    invalid = tmp_path / "merged_invalid_words.txt"
    invalid.write_text("\n".join(words) + "\n", encoding="utf-8")
    valid = tmp_path / "merged_valid_words.txt"
    valid.write_text("", encoding="utf-8")
    valid_dict = tmp_path / "merged_valid_dict.json"
    valid_dict.write_text("{}", encoding="utf-8")

    for name, path in [("INVALID_WORDS_FILE", invalid), ("VALID_WORDS_FILE", valid),
                       ("VALID_DICT_FILE", valid_dict),
                       ("RECHECK_QUEUE_FILE", tmp_path / "no_queue.txt"),
                       ("OUTPUT_DIR", tmp_path / "output")]:
        monkeypatch.setattr(validate_module, name, path)

    v = InvalidListValidator()
    v.progress_file = tmp_path / "validation_progress.json"
    return v, words, tmp_path


def test_unchecked_words_get_no_date(night):
    v, words, _ = night
    # Collegiate rules on 2 words and is over quota for the rest of the night.
    v.api_client = client(FakeSource({
        "steamship": (WordStatus.VALID, None),
        "horrid": (WordStatus.NOT_FOUND, None),
    }, default=WordStatus.ERROR, http_status=429))
    v.word_validator.validate = lambda w: type("R", (), {"is_valid": True})()

    order = ["steamship", "horrid", "initial", "rallying"]
    v.prioritizer.prioritize_words = lambda pool, budget: [
        type("C", (), {"word": w, "score": 1.0, "reasons": []})() for w in order if w in pool
    ][:budget]

    results = run(v.run_daily_validation(limit=4))
    progress = json.loads(v.progress_file.read_text())

    assert results["selected"] == 4
    assert results["validated"] == 2
    assert results["promoted_words"] == ["steamship"]
    assert results["not_checked"] == 2
    assert results["not_checked_by_status"] == {"429": 2}
    assert results["refused_sources"] == {"collegiate": 429}
    assert set(progress["checked"]) == {"steamship", "horrid"}
    assert progress["validated_count"] == 2
    assert exit_code(results) == 0


def test_a_night_that_checks_nothing_exits_nonzero(night):
    v, _, _ = night
    v.api_client = client(FakeSource({}, default=WordStatus.ERROR, http_status=403))
    v.word_validator.validate = lambda w: type("R", (), {"is_valid": True})()

    results = run(v.run_daily_validation(limit=4, sample_mode=True))

    assert results["validated"] == 0 and results["not_checked"] == 4
    assert exit_code(results) == 1


@pytest.mark.skipif(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="needs POSIX modes and a user that file modes apply to")
def test_read_only_source_files_stop_the_night_before_any_lookup(night):
    v, _, tmp_path = night
    os.chmod(tmp_path / "merged_valid_dict.json", 0o444)
    collegiate = FakeSource({})
    v.api_client = client(collegiate)

    results = run(v.run_daily_validation(limit=4, sample_mode=True))

    assert results["success"] is False
    assert collegiate.asked == []
    assert exit_code(results) == 1


def test_the_summary_file_carries_counts_and_no_words(night, monkeypatch):
    _, _, tmp_path = night
    monkeypatch.setattr(validate_module, "get_release_date", lambda: "2026-10-30")
    validate_module.write_validation_summary({
        "success": True, "selected": 2, "validated": 1, "promoted": 1,
        "promoted_words": ["steamship"], "not_checked": 1,
    })
    summary = json.loads((tmp_path / "output" / "2026-10-30" / "validation_summary.json").read_text())
    assert "promoted_words" not in summary
    assert summary["not_checked"] == 1


# --------------------------------------------------- 4. failure fails the step

def test_nothing_to_validate_is_not_a_failure():
    assert exit_code({"success": True, "validated": 0, "promoted_words": []}) == 0


def test_a_failed_validation_exits_nonzero():
    assert exit_code({"success": False}) == 1


def test_a_failed_update_exits_nonzero():
    assert update_exit_code({"success": False, "error": "Permission denied"}) == 1
    assert update_exit_code({"success": True}) == 0


def test_discovery_no_longer_scrapes_the_new_words_page():
    from config import NEW_WORD_SOURCES
    from scripts.run_weekly_update import NewWordDiscoverer

    assert "merriam_webster_new_words" not in NEW_WORD_SOURCES
    assert not hasattr(NewWordDiscoverer, "discover_from_mw_new_words_page")
