"""
Tests for the data correction ledger.

The ledger is the source of truth for every word this correction moves: the
lists are regenerated from it, so a mistake here becomes a mistake in the
dataset. These tests hold the two properties that make it safe to run.

  1. It only rules on words that carry a recorded dictionary ruling. Anything
     else is reported as unresolved and left alone, rather than guessed at.
  2. It never removes a word from the invalid list that is not in the valid
     list. That would be deleting a word, not correcting one, and the whole
     point of stage 1 is that a word must be on exactly one side.

Also guards the enum leak that produced `"status": "WordStatus.VALID"` on 201
entries — see scripts/dictionary_api.py.
"""

import csv
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.build_correction_ledger import (
    build_stage1_rows,
    describe_evidence,
    find_dual_listed,
)
from scripts.apply_correction_ledger import (
    ENUM_LEAK,
    apply_removals,
    normalise_status,
)
from scripts.dictionary_api import WordStatus


DECIDED = "2026-08-13"


def test_enum_does_not_leak_its_repr():
    """str() on a member gives the value, so a stray f-string cannot corrupt the data."""
    assert str(WordStatus.VALID) == "valid"
    assert str(WordStatus.NOT_FOUND) == "not_found"
    assert f"{WordStatus.VALID}" != ENUM_LEAK


def test_normalise_status_repairs_only_the_leak():
    valid_dict = {
        "mpox": {"status": ENUM_LEAK},
        "aaugh": {"status": "invalid"},
        "a": {"status": "valid"},
        "aalii": {},
    }
    assert normalise_status(valid_dict) == 1
    assert valid_dict["mpox"]["status"] == "valid"
    # An LLM's "invalid" verdict is a verdict, not a serialisation bug. Leave it.
    assert valid_dict["aaugh"]["status"] == "invalid"
    assert valid_dict["a"]["status"] == "valid"
    assert "status" not in valid_dict["aalii"]


def test_find_dual_listed_is_the_intersection_and_sorted():
    assert find_dual_listed({"b", "a", "c"}, {"c", "a", "z"}) == ["a", "c"]
    assert find_dual_listed({"a"}, {"b"}) == []


def test_ledger_rules_only_on_words_with_an_authoritative_source():
    valid_dict = {
        "mpox": {"source": "merriam-webster", "part_of_speech": "noun",
                 "definition": "a zoonotic disease"},
        "aalii": {"source": "synthetic_generation"},
        "budr": {"source": "invalid_list_recovery"},
    }
    rows, unresolved = build_stage1_rows(["aalii", "budr", "mpox"], valid_dict, DECIDED)

    assert [r["word"] for r in rows] == ["mpox"]
    assert sorted(unresolved) == ["aalii", "budr"]

    row = rows[0]
    assert row["verdict"] == "valid"
    assert row["action"] == "remove_from_invalid_list"
    assert row["method"] == "stored_api_ruling"
    assert row["source"] == "merriam-webster"
    assert row["decided_date"] == DECIDED


def test_ledger_reports_a_dual_listed_word_missing_from_the_dict():
    rows, unresolved = build_stage1_rows(["ghost"], {}, DECIDED)
    assert rows == []
    assert unresolved == ["ghost"]


def test_evidence_describes_what_is_recorded():
    assert describe_evidence({"raw_response": {"meta": {}}, "definition": "x"}) == \
        "raw_response+definition"
    assert describe_evidence({}) == "none"


def test_apply_removes_exactly_the_ledger_words():
    rows = [{"word": "mpox", "action": "remove_from_invalid_list"}]
    valid = {"mpox", "hashtag"}
    invalid = {"mpox", "zzzz"}

    new_invalid, removed = apply_removals(rows, valid, invalid)

    assert removed == ["mpox"]
    assert new_invalid == {"zzzz"}
    assert not (valid & new_invalid)


def test_apply_refuses_to_delete_a_word_that_is_not_in_the_valid_list():
    """
    The ledger's premise is that the word belongs on the valid side. If it is not
    there, removing it from the invalid list would delete it from the dataset
    entirely — so stop rather than execute.
    """
    rows = [{"word": "zzzz", "action": "remove_from_invalid_list"}]
    with pytest.raises(ValueError, match="could not be applied safely"):
        apply_removals(rows, valid={"mpox"}, invalid={"zzzz"})


def test_apply_rejects_an_action_it_does_not_recognise():
    rows = [{"word": "mpox", "action": "demote_to_invalid"}]
    with pytest.raises(ValueError, match="unrecognised action"):
        apply_removals(rows, valid={"mpox"}, invalid={"mpox"})


def test_apply_is_idempotent():
    """Re-running against already-corrected data changes nothing and does not raise."""
    rows = [{"word": "mpox", "action": "remove_from_invalid_list"}]
    new_invalid, removed = apply_removals(rows, valid={"mpox"}, invalid={"zzzz"})
    assert removed == []
    assert new_invalid == {"zzzz"}


def test_shipped_stage1_ledger_is_well_formed():
    """The ledger that actually shipped, checked against its own rules."""
    path = Path(__file__).parent.parent / "corrections" / "ledger_stage1.csv"
    if not path.exists():
        pytest.skip("stage 1 ledger not present")

    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 150, "stage 1 covered 150 dual-listed words"
    assert {r["action"] for r in rows} == {"remove_from_invalid_list"}
    assert {r["verdict"] for r in rows} == {"valid"}
    assert {r["method"] for r in rows} == {"stored_api_ruling"}
    assert {r["source"] for r in rows} <= {
        "merriam-webster", "merriam-webster-medical", "free-dictionary"
    }
    assert len({r["word"] for r in rows}) == len(rows), "no duplicate words"
    assert all(r["evidence"] != "none" for r in rows), "every verdict cites evidence"
