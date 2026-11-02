"""The published records leave out the withheld labels and the dictionaries' text."""

import sys
from pathlib import Path

import orjson

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.publication_filter import clean_dictionary, clean_file, clean_record


def test_the_tournament_and_merriam_webster_sources_are_renamed():
    rows = {
        "a": {"word": "a", "source": "twl_scrabble_dictionary"},
        "b": {"word": "b", "source": "merriam-webster"},
        "c": {"word": "c", "source": "merriam-webster-medical"},
    }
    clean_dictionary(rows)
    assert rows["a"]["source"] == "withheld_intake"
    assert rows["b"]["source"] == rows["c"]["source"] == "withheld_dictionary"


def test_other_sources_pass_unchanged():
    for source in ("free-dictionary", "synthetic_generation", "invalid_list_recovery", "authoritative_extracts"):
        record = clean_record({"source": source})
        assert record["source"] == source


def test_four_discovery_sources_are_dropped_with_either_suffix():
    record = clean_record({"candidate_source": [
        "google_ngrams_valid", "coca_frequency_valid", "coca_frequency_unlikely", "collins_unlikely",
        "linux_valid", "linux_unlikely", "nltk_valid", "nltk_unlikely", "wordnet_valid", "enable_valid",
    ]})
    assert record["candidate_source"] == ["google_ngrams_valid", "wordnet_valid", "enable_valid"]


def test_a_word_whose_whole_log_is_withheld_keeps_an_empty_list():
    assert clean_record({"candidate_source": ["linux_valid", "nltk_valid"]})["candidate_source"] == []


def test_dictionary_text_goes_and_the_verdict_stays():
    record = clean_record({
        "word": "x", "dictionary_verdict": "valid", "part_of_speech": "noun", "source": "free-dictionary",
        "definition": "d", "pronunciation": "p", "etymology": "e", "raw_response": {"meanings": []},
    })
    assert set(record) == {"word", "dictionary_verdict", "part_of_speech", "source"}


def test_the_filter_is_idempotent_and_leaves_a_clean_file_alone(tmp_path):
    path = tmp_path / "merged_valid_dict.json"
    original = {"a": {"word": "a", "source": "twl_scrabble_dictionary", "candidate_source": ["nltk_valid", "x_valid"]}}
    path.write_bytes(orjson.dumps(original, option=orjson.OPT_INDENT_2))
    first = clean_file(path)
    assert first.changed and first.sources == 1 and first.discovery_entries == 1
    after = path.read_bytes()
    second = clean_file(path)
    assert not second.changed and path.read_bytes() == after
    assert b"twl_scrabble" not in after and b"nltk" not in after


def test_the_push_cleans_both_copies_before_it_uploads(tmp_path, monkeypatch):
    import scripts.push_to_huggingface as push

    row = {"w": {"word": "w", "source": "twl_scrabble_dictionary", "raw_response": {"x": 1}}}
    data_dir, release = tmp_path / "data", tmp_path / "release"
    data_dir.mkdir(), release.mkdir()
    for folder in (data_dir, release):
        (folder / "merged_valid_dict.json").write_bytes(orjson.dumps(row, option=orjson.OPT_INDENT_2))

    seen = {}

    class FakeUploader:
        def upload_release(self, **kwargs):
            seen["release"] = (release / "merged_valid_dict.json").read_bytes()
            return True

        def upload_brrrdle_artifacts(self, **kwargs):
            return True

        def upload_full_wordlists(self, message=None, data_dir=None):
            seen["full"] = (data_dir / "merged_valid_dict.json").read_bytes()
            seen["message"] = message
            return True

        def upload_dataset_card(self):
            return True

    monkeypatch.setattr(push, "HuggingFaceUploader", FakeUploader)
    monkeypatch.setattr(sys, "argv", ["push", "--release-dir", str(release), "--data-dir", str(data_dir)])
    assert push.main() == 0
    for key in ("release", "full"):
        assert b"twl_scrabble" not in seen[key] and b"raw_response" not in seen[key]
    assert "withheld" in seen["message"]
