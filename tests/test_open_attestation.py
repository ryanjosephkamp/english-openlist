"""`attested_by` names the open sources whose files list a word, in a fixed order."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.open_attestation import ATTESTING_KEYS, Attester, count


def lists(**words):
    return {key: set(words.get(key, ())) for key in ATTESTING_KEYS}


def test_sources_come_back_in_the_fixed_order():
    attester = Attester(lists(wordfreq={"broth"}, wiktionary={"broth"}, scowl={"broth"}))
    assert attester.sources_of("broth") == ["wiktionary", "scowl", "wordfreq"]


def test_a_word_no_source_lists_gets_an_empty_list():
    assert Attester(lists(scowl={"broth"})).sources_of("brothx") == []


def test_wordnet_also_counts_a_form_its_morphology_maps_to_a_lemma():
    attester = Attester(lists(wordnet={"abacus"}), morphy=lambda word: word == "abacuses")
    assert attester.sources_of("abacuses") == ["wordnet"]
    assert attester.sources_of("abacusez") == []


def test_morphology_applies_to_wordnet_only():
    attester = Attester(lists(), morphy=lambda word: True)
    assert attester.sources_of("anything") == ["wordnet"]


def test_an_unknown_source_is_refused():
    with pytest.raises(ValueError):
        Attester({"somewhere": {"broth"}})


def test_a_missing_list_is_refused(tmp_path):
    (tmp_path / "wiktionary.txt").write_text("broth\n")
    with pytest.raises(FileNotFoundError):
        Attester.from_directory(tmp_path, use_morphy=False)


def test_lists_are_read_from_a_directory(tmp_path):
    for key in ATTESTING_KEYS:
        (tmp_path / f"{key}.txt").write_text("Broth\n\n" if key == "enable" else "")
    attester = Attester.from_directory(tmp_path, use_morphy=False)
    assert attester.sources_of("broth") == ["enable"]


def test_counts_cover_every_source_and_the_unlisted():
    totals = count({"a": ["wiktionary", "scowl"], "b": [], "c": ["scowl"]})
    assert totals["scowl"] == 2 and totals["wiktionary"] == 1 and totals["none"] == 1
    assert set(totals) == {*ATTESTING_KEYS, "none"}
