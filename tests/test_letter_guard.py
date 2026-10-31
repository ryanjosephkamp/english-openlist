"""
Tests for the nightly's single-letter guard.

D-027 asserts `a` and `i` and makes the other 24 letters candidates, to be
adjudicated on evidence. A dictionary's entry for a letter names the character,
so a lookup would promote every one of them. Before the guard, 4 runs, from
August 22 to October 30, 2026, promoted one each through the recheck queue,
which bypasses the pre-filter. These tests hold both nightly paths, the
invalid-list check and new-word discovery, to never ask about one of those
letters, and so never to promote one.
"""

import asyncio
import json
import string
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.run_weekly_update as update_module  # noqa: E402
import scripts.validate_invalid_list as validate_module  # noqa: E402
from config import ASSERTED_LETTERS, nightly_may_promote  # noqa: E402
from scripts.data_updater import UpdateStats  # noqa: E402
from scripts.dictionary_api import DictionaryAPIClient, WordLookupResult, WordStatus  # noqa: E402
from scripts.run_weekly_update import WeeklyUpdatePipeline  # noqa: E402
from scripts.validate_invalid_list import InvalidListValidator  # noqa: E402
from scripts.word_validator import WordValidator  # noqa: E402

# The 24 letters D-027 leaves to adjudication, built rather than listed.
LETTERS = [c for c in string.ascii_lowercase if c not in ASSERTED_LETTERS]
WORDS = ["steamship", "sincerity", "aflatoxin"]


class EveryWordSource:
    """A dictionary that recognizes everything, as one would every letter."""

    def __init__(self):
        self.asked: list[str] = []
        self.is_configured = True

    async def lookup_word(self, word: str) -> WordLookupResult:
        self.asked.append(word)
        return WordLookupResult(word=word, status=WordStatus.VALID)


def client(collegiate):
    c = DictionaryAPIClient.__new__(DictionaryAPIClient)
    c.mw = collegiate
    c.mw_medical = EveryWordSource()
    c.free_dict = EveryWordSource()
    c.refused = {}
    return c


def test_only_a_and_i_among_the_letters():
    assert ASSERTED_LETTERS == {"a", "i"}
    assert [c for c in string.ascii_lowercase if nightly_may_promote(c)] == ["a", "i"]
    assert all(nightly_may_promote(w) for w in WORDS + ["regift"])


@pytest.mark.parametrize("sample_mode", [False, True])
def test_the_invalid_list_check_passes_over_the_letters(tmp_path, monkeypatch, sample_mode):
    invalid = tmp_path / "merged_invalid_words.txt"
    invalid.write_text("\n".join(LETTERS + WORDS) + "\n", encoding="utf-8")
    queue = tmp_path / "recheck_queue.txt"
    queue.write_text("# letters and a word\n" + "\n".join(LETTERS + ["aflatoxin"]) + "\n",
                     encoding="utf-8")
    valid = tmp_path / "merged_valid_words.txt"
    valid.write_text("", encoding="utf-8")
    valid_dict = tmp_path / "merged_valid_dict.json"
    valid_dict.write_text("{}", encoding="utf-8")
    for name, path in [("INVALID_WORDS_FILE", invalid), ("VALID_WORDS_FILE", valid),
                       ("VALID_DICT_FILE", valid_dict), ("RECHECK_QUEUE_FILE", queue),
                       ("OUTPUT_DIR", tmp_path / "output")]:
        monkeypatch.setattr(validate_module, name, path)

    v = InvalidListValidator()
    v.progress_file = tmp_path / "validation_progress.json"
    collegiate = EveryWordSource()
    v.api_client = client(collegiate)

    results = asyncio.run(v.run_daily_validation(limit=100, sample_mode=sample_mode))
    progress = json.loads(v.progress_file.read_text())

    assert not set(collegiate.asked) & set(LETTERS)
    assert "aflatoxin" in collegiate.asked
    assert sorted(results["promoted_words"]) == sorted(
        w for w in WORDS if w in collegiate.asked
    )
    assert not set(progress["checked"]) & set(LETTERS)


def test_discovery_passes_over_the_letters(monkeypatch, tmp_path):
    for name in ("VALID_WORDS_FILE", "VALID_DICT_FILE"):
        monkeypatch.setattr(update_module, name, tmp_path / name)

    p = WeeklyUpdatePipeline.__new__(WeeklyUpdatePipeline)
    p.release_date = "2026-10-31"
    p.release_dir = tmp_path
    p.discovered_words, p.validated_words, p.not_checked = [], [], []

    async def discover_all():
        return LETTERS + ["regift"]

    p.discoverer = type("D", (), {"discover_all": staticmethod(discover_all)})()
    p.data_manager = type("M", (), {"load_data": lambda self: None,
                                    "valid_words": set(), "invalid_words": set()})()
    p.validator = WordValidator()
    collegiate = EveryWordSource()
    p.api_client = client(collegiate)

    added = []

    def run_update(words, release_dir):
        added.extend(w["word"] for w in words)
        return UpdateStats(words_added_to_valid=len(words))

    p.updater = type("U", (), {"run_update": staticmethod(run_update)})()
    p._save_update_stats = lambda: None
    p._generate_changelog = lambda: None

    result = asyncio.run(p.run())

    assert result["success"]
    assert collegiate.asked == ["regift"]
    assert added == ["regift"]
