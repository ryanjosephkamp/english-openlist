"""
Tests for the dictionary client's parsing and its response cache.

Two things are being held in place here.

**The entry scan.** These APIs return a list of entries and the exact match is
not reliably first — Merriam-Webster returns anything whose stems contain the
query, so a lookup can come back headed by a related word. Reading only
`data[0]` reported NOT_FOUND for words the dictionary genuinely holds, and
`validate_invalid_list.py` treats "not found" as "not a word", so the error ran
in the damaging direction. The scan must not regress into an index.

**The cache's default.** It is off unless EOL_DICT_CACHE says otherwise. The
nightly run promotes words into a published dataset unattended; a stale cached
"not found" would freeze a word out of promotion indefinitely. The measurement
work opts in, the pipeline does not.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.dictionary_api import (
    FreeDictionaryAPI,
    MerriamWebsterAPI,
    MerriamWebsterMedicalAPI,
    ResponseCache,
    WordStatus,
    _first_matching_entry,
    cache_enabled,
)


def mw_entry(headword: str, fl: str = "noun", stems=None) -> dict:
    """A Merriam-Webster entry, trimmed to the fields the parser reads."""
    return {
        "meta": {"id": headword, "stems": stems or [headword]},
        "hwi": {"hw": headword},
        "fl": fl,
        "def": [{"sseq": [[["sense", {"dt": [["text", "{bc}a definition"]]}]]]}],
    }


# --------------------------------------------------------------- the entry scan

def test_first_matching_entry_finds_a_later_match():
    data = [{"word": "other"}, {"word": "another"}, {"word": "target"}]
    assert _first_matching_entry(data, lambda e: e.get("word") == "target") == {"word": "target"}


def test_first_matching_entry_returns_none_when_nothing_matches():
    assert _first_matching_entry([{"word": "a"}], lambda e: e.get("word") == "z") is None


def test_first_matching_entry_skips_non_dict_items():
    """MW returns a list of strings for spelling suggestions; they are not entries."""
    data = ["suggestion", {"word": "target"}]
    assert _first_matching_entry(data, lambda e: e.get("word") == "target") == {"word": "target"}


def test_collegiate_finds_the_match_behind_a_related_headword():
    """The regression this whole scan exists for."""
    api = MerriamWebsterAPI(api_key="x", cache=ResponseCache("t", enabled=False))
    data = [mw_entry("mind"), mw_entry("minder"), mw_entry("abacavir")]

    result = api._parse_response("abacavir", data)

    assert result.status == WordStatus.VALID
    assert result.raw_response["meta"]["id"] == "abacavir"


def test_collegiate_still_reports_not_found_when_no_entry_matches():
    api = MerriamWebsterAPI(api_key="x", cache=ResponseCache("t", enabled=False))
    result = api._parse_response("zzzzz", [mw_entry("mind"), mw_entry("minder")])
    assert result.status == WordStatus.NOT_FOUND


def test_collegiate_treats_spelling_suggestions_as_not_found():
    api = MerriamWebsterAPI(api_key="x", cache=ResponseCache("t", enabled=False))
    result = api._parse_response("noher", ["nosher", "gopher"])
    assert result.status == WordStatus.NOT_FOUND


def test_collegiate_matches_on_an_inflected_stem():
    """MW lists inflections in meta.stems, which is how a plural resolves."""
    api = MerriamWebsterAPI(api_key="x", cache=ResponseCache("t", enabled=False))
    data = [mw_entry("abacavir", stems=["abacavir", "abacavirs"])]
    assert api._parse_response("abacavirs", data).status == WordStatus.VALID


def test_collegiate_screens_abbreviations_from_a_later_entry():
    api = MerriamWebsterAPI(api_key="x", cache=ResponseCache("t", enabled=False))
    data = [mw_entry("unrelated"), mw_entry("acsw", fl="abbreviation")]
    assert api._parse_response("acsw", data).status == WordStatus.ABBREVIATION


def test_medical_finds_the_match_behind_a_related_headword():
    api = MerriamWebsterMedicalAPI(api_key="x", cache=ResponseCache("t", enabled=False))
    data = [mw_entry("abdomen"), mw_entry("abambulacral")]
    assert api._parse_response("abambulacral", data).status == WordStatus.VALID


def test_free_dictionary_finds_a_later_match():
    api = FreeDictionaryAPI(cache=ResponseCache("t", enabled=False))
    data = [
        {"word": "other", "meanings": []},
        {"word": "bockety", "meanings": [
            {"partOfSpeech": "adjective", "definitions": [{"definition": "wobbly"}]}
        ]},
    ]
    result = api._parse_response("bockety", data)
    assert result.status == WordStatus.VALID
    assert result.part_of_speech == "adjective"


def test_free_dictionary_still_accepts_an_entry_with_no_word_field():
    """
    The pre-scan code accepted these, because its guard was `if entry_word and
    entry_word != word`. The scan must not quietly start rejecting them.
    """
    api = FreeDictionaryAPI(cache=ResponseCache("t", enabled=False))
    data = [{"meanings": [{"partOfSpeech": "noun", "definitions": [{"definition": "x"}]}]}]
    assert api._parse_response("whatever", data).status == WordStatus.VALID


# ---------------------------------------------------------------------- the cache

def test_cache_is_off_by_default(monkeypatch):
    """The nightly must not silently start reading cached verdicts."""
    monkeypatch.delenv("EOL_DICT_CACHE", raising=False)
    assert cache_enabled() is False
    assert ResponseCache("collegiate").enabled is False


@pytest.mark.parametrize("value,expected", [
    ("1", True), ("true", True), ("YES", True), ("on", True),
    ("0", False), ("false", False), ("", False), ("maybe", False),
])
def test_cache_env_gate(monkeypatch, value, expected):
    monkeypatch.setenv("EOL_DICT_CACHE", value)
    assert cache_enabled() is expected


def test_disabled_cache_reads_nothing_and_writes_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.dictionary_api.CACHE_DIR", tmp_path)
    cache = ResponseCache("collegiate", enabled=False)
    cache.put("mpox", [{"meta": {"id": "mpox"}}])
    assert cache.get("mpox") is None
    assert not (tmp_path / "collegiate.jsonl").exists()


def test_cache_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.dictionary_api.CACHE_DIR", tmp_path)
    payload = [{"meta": {"id": "mpox"}}]

    writer = ResponseCache("collegiate", enabled=True)
    writer.put("mpox", payload, 200)

    reader = ResponseCache("collegiate", enabled=True)
    assert reader.get("mpox") == payload
    assert reader.hits == 1
    assert reader.get("absent") is None
    assert reader.misses == 1


def test_cache_stores_the_raw_payload_not_a_verdict(tmp_path, monkeypatch):
    """
    So a parser fix applies retroactively to everything already fetched, and a
    verdict can be re-derived without spending quota.
    """
    monkeypatch.setattr("scripts.dictionary_api.CACHE_DIR", tmp_path)
    ResponseCache("collegiate", enabled=True).put("mpox", [mw_entry("mpox")], 200)

    record = json.loads((tmp_path / "collegiate.jsonl").read_text().strip())
    assert record["word"] == "mpox"
    assert record["http_status"] == 200
    assert record["payload"][0]["meta"]["id"] == "mpox"
    assert "fetched_at" in record


def test_cache_survives_a_truncated_final_line(tmp_path, monkeypatch):
    """An interrupted run leaves a half-written line; it should cost one word, not the file."""
    monkeypatch.setattr("scripts.dictionary_api.CACHE_DIR", tmp_path)
    path = tmp_path / "collegiate.jsonl"
    good = json.dumps({"word": "mpox", "payload": [1], "fetched_at": "t", "http_status": 200})
    path.write_text(good + '\n{"word": "trunc", "payl')

    cache = ResponseCache("collegiate", enabled=True)
    assert cache.get("mpox") == [1]
    assert cache.get("trunc") is None
