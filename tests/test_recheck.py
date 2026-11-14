"""
Tests for re-validation eligibility.

A demoted word must never become permanently invalid. It was moved off the valid
list because no dictionary we could reach recognised it *today*; dictionaries
gain entries, and some of these forms may yet be attested. If the pipeline can
never look at them again, the demotion is a life sentence handed down on a
single afternoon's evidence.

Three separate mechanisms could have made that happen, and each has a test here:

  1. `validation_progress.json` accumulated every word ever checked and filtered
     it out of every future run. Permanent, and it was already excluding 2,005
     words. Now a dated cooldown.
  2. The prioritiser's `is_likely_english` pre-filter drops anything over 15
     characters, which covers 4,932 of the 16,478 demoted comparatives. The
     recheck queue bypasses it.
  3. 9.29 million invalid words at 1,000 a day is a 25-year cycle. The queue
     reserves a slice of each night so demoted words rotate in months.
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from config import RECHECK_AFTER_DAYS, RECHECK_DAILY_SLICE
from scripts.validate_invalid_list import InvalidListValidator, WordPrioritizer


def days_ago(n: int) -> str:
    return (datetime.now() - timedelta(days=n)).date().isoformat()


@pytest.fixture
def validator(tmp_path, monkeypatch):
    v = InvalidListValidator()
    v.progress_file = tmp_path / "validation_progress.json"
    return v


# ------------------------------------------------- 1. the cooldown, not a bar

def test_a_recently_checked_word_is_skipped(validator, tmp_path, monkeypatch):
    invalid = tmp_path / "invalid.txt"
    invalid.write_text("aaa\nbbb\n", encoding="utf-8")
    monkeypatch.setattr("scripts.validate_invalid_list.INVALID_WORDS_FILE", invalid)

    validator.progress_file.write_text(json.dumps({
        "validated_count": 1, "promoted_count": 0, "last_run": None,
        "checked": {"aaa": days_ago(3)},
    }))
    assert validator.load_invalid_words() == ["bbb"]


def test_a_word_checked_long_ago_becomes_eligible_again(validator, tmp_path, monkeypatch):
    """The whole point: no word is invalid for good."""
    invalid = tmp_path / "invalid.txt"
    invalid.write_text("aaa\nbbb\n", encoding="utf-8")
    monkeypatch.setattr("scripts.validate_invalid_list.INVALID_WORDS_FILE", invalid)

    validator.progress_file.write_text(json.dumps({
        "validated_count": 1, "promoted_count": 0, "last_run": None,
        "checked": {"aaa": days_ago(RECHECK_AFTER_DAYS + 1)},
    }))
    assert validator.load_invalid_words() == ["aaa", "bbb"]


def test_the_old_permanent_list_is_migrated_to_dates(validator):
    """
    Files written before this change carry `validated_words`, a flat list. They
    must not be read as "check these never again", and must not all come due at
    once either — so they are stamped with the last run date.
    """
    validator.progress_file.write_text(json.dumps({
        "validated_count": 2, "promoted_count": 0,
        "last_run": "2026-08-14T00:34:13",
        "validated_words": ["aaa", "bbb"],
    }))
    progress = validator.load_progress()

    assert "validated_words" not in progress
    assert progress["checked"] == {"aaa": "2026-08-14", "bbb": "2026-08-14"}


def test_a_fresh_progress_file_uses_the_new_shape(validator):
    assert validator.load_progress()["checked"] == {}


# ------------------------------------- 2. the queue bypasses the pre-filter

def test_the_prefilter_would_hide_long_demoted_words():
    """
    Establishes the problem the queue exists to solve, so that if the
    pre-filter is ever loosened this test says so rather than quietly passing.
    """
    p = WordPrioritizer()
    assert not p.is_likely_english("abdominocutaneousest")   # 20 chars
    assert not p.is_likely_english("laryngoscopicalest")     # 18 chars
    assert p.is_likely_english("abatabler")


def test_the_queue_returns_words_the_prefilter_rejects(validator, tmp_path, monkeypatch):
    queue = tmp_path / "recheck_queue.txt"
    queue.write_text("abdominocutaneousest\nabatabler\n", encoding="utf-8")
    monkeypatch.setattr("scripts.validate_invalid_list.RECHECK_QUEUE_FILE", queue)

    due = validator.load_recheck_queue({"abdominocutaneousest", "abatabler"}, {})
    assert "abdominocutaneousest" in due, "the queue must not apply the pre-filter"
    assert "abatabler" in due


def test_the_queue_ignores_comments_and_blank_lines(validator, tmp_path, monkeypatch):
    queue = tmp_path / "recheck_queue.txt"
    queue.write_text("# demoted 2026-08-14\n\nabatabler\n", encoding="utf-8")
    monkeypatch.setattr("scripts.validate_invalid_list.RECHECK_QUEUE_FILE", queue)
    assert validator.load_recheck_queue({"abatabler"}, {}) == ["abatabler"]


def test_the_queue_only_offers_words_that_are_eligible_today(validator, tmp_path, monkeypatch):
    """A queued word still cooling off is not due; the cooldown is not bypassed."""
    queue = tmp_path / "recheck_queue.txt"
    queue.write_text("aaa\nbbb\n", encoding="utf-8")
    monkeypatch.setattr("scripts.validate_invalid_list.RECHECK_QUEUE_FILE", queue)
    assert validator.load_recheck_queue({"bbb"}, {}) == ["bbb"]


def test_the_queue_rotates_oldest_checked_first(validator, tmp_path, monkeypatch):
    queue = tmp_path / "recheck_queue.txt"
    queue.write_text("recent\nancient\nnever\n", encoding="utf-8")
    monkeypatch.setattr("scripts.validate_invalid_list.RECHECK_QUEUE_FILE", queue)

    due = validator.load_recheck_queue(
        {"recent", "ancient", "never"},
        {"recent": days_ago(1), "ancient": days_ago(400)},
    )
    assert due == ["never", "ancient", "recent"]


def test_the_queue_respects_its_daily_slice(validator, tmp_path, monkeypatch):
    queue = tmp_path / "recheck_queue.txt"
    words = [f"word{i}" for i in range(RECHECK_DAILY_SLICE + 50)]
    queue.write_text("\n".join(words), encoding="utf-8")
    monkeypatch.setattr("scripts.validate_invalid_list.RECHECK_QUEUE_FILE", queue)

    assert len(validator.load_recheck_queue(set(words), {})) == RECHECK_DAILY_SLICE


def test_a_missing_queue_is_not_an_error(validator, tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.validate_invalid_list.RECHECK_QUEUE_FILE",
                        tmp_path / "absent.txt")
    assert validator.load_recheck_queue({"aaa"}, {}) == []


# --------------------------------------------------- 3. the file stays bounded

def test_the_shipped_queue_covers_every_demoted_word():
    """If a word was demoted, it is queued for another look. No exceptions."""
    queue_path = ROOT / "corrections" / "recheck_queue.txt"
    ledger_path = ROOT / "corrections" / "ledger_demotions.csv"
    if not (queue_path.exists() and ledger_path.exists()):
        pytest.skip("nothing demoted yet")

    import csv
    with open(ledger_path, encoding="utf-8", newline="") as f:
        demoted = {r["word"] for r in csv.DictReader(f)}
    queued = {line.strip() for line in open(queue_path, encoding="utf-8")
              if line.strip() and not line.startswith("#")}

    assert demoted, "ledger is empty"
    assert demoted <= queued, f"{len(demoted - queued)} demoted words are not queued"
