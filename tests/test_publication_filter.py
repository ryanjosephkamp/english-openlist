"""Every published record has the same few fields, and nothing else."""

import sys
from pathlib import Path

import orjson

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.publication_filter import (
    PUBLISHED_FIELDS,
    PUBLISHED_SOURCES,
    clean_file,
    project_dictionary,
    project_record,
)


def test_a_record_keeps_only_the_published_fields():
    record = project_record("abacus", {
        "word": "abacus", "attested_by": ["scowl", "wiktionary"], "candidate_source": ["wordnet_valid"],
        "manual_validation": {"x": 1}, "unverified_llm_verdict": "valid", "added_date": "2025-12-17",
        "definition": "d", "raw_response": {"meanings": []},
    })
    assert record == {"word": "abacus", "length": 6, "attested_by": ["wiktionary", "scowl"]}


def test_published_sources_keep_their_source_and_day():
    for source in PUBLISHED_SOURCES:
        record = project_record("w", {"source": source, "added_date": "2026-08-12T00:31:32.232007"})
        assert record["source"] == source and record["added_date"] == "2026-08-12"


def test_the_date_falls_back_to_the_other_date_fields():
    record = project_record("w", {"source": "synthetic_generation", "created_date": "2026-01-11T12:19:00"})
    assert record["added_date"] == "2026-01-11"


def test_any_other_source_goes_with_its_date():
    record = project_record("w", {"source": "some_unpublished_list", "added_date": "2026-01-10", "length": 1})
    assert record == {"word": "w", "length": 1}


def test_records_from_different_intakes_end_up_the_same_shape():
    rows = {
        "aa": {"source": "some_unpublished_list", "validation_status": "valid", "added_date": "2026-01-10", "length": 2,
               "attested_by": ["scowl"]},
        "ab": {"candidate_source": ["google_ngrams_valid"], "validation_source": "verification_pipeline",
               "added_date": "2025-12-17", "attested_by": ["scowl"]},
    }
    published, counts = project_dictionary(rows)
    assert set(published["aa"]) == set(published["ab"]) == {"word", "length", "attested_by"}
    assert counts.sources_dropped == 1


def test_attestation_keys_are_known_and_in_order():
    record = project_record("w", {"attested_by": ["wordfreq", "nonsense", "wiktionary"]})
    assert record["attested_by"] == ["wiktionary", "wordfreq"]


def test_the_dictionary_comes_out_sorted_by_word():
    published, counts = project_dictionary({"b": {}, "a": {}, "c": {}})
    assert list(published) == ["a", "b", "c"] and counts.changed


def test_the_projection_is_idempotent_and_leaves_a_clean_file_alone(tmp_path):
    path = tmp_path / "merged_valid_dict.json"
    original = {
        "b": {"source": "some_unpublished_list", "candidate_source": ["x_valid"]},
        "a": {"source": "invalid_list_recovery", "added_date": "2026-11-01", "validation_status": "valid"},
    }
    path.write_bytes(orjson.dumps(original, option=orjson.OPT_INDENT_2))
    first = clean_file(path)
    assert first.changed and first.sources_dropped == 1
    after = path.read_bytes()
    second = clean_file(path)
    assert not second.changed and path.read_bytes() == after
    assert b"some_unpublished_list" not in after and b"candidate_source" not in after
    for record in orjson.loads(after).values():
        assert set(record) <= set(PUBLISHED_FIELDS)


def test_the_push_cleans_both_copies_before_it_uploads(tmp_path, monkeypatch):
    import scripts.push_to_huggingface as push

    row = {"w": {"word": "w", "source": "some_unpublished_list", "raw_response": {"x": 1}}}
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
        assert b"some_unpublished_list" not in seen[key] and b"raw_response" not in seen[key]
    assert seen["message"] == "Reduce the records to their published fields"
