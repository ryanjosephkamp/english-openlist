import json
import math
import sys
from itertools import islice, product
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.generate_brrrdle_artifacts import (
    CURATION_METHOD,
    CURATION_NOTE,
    MAX_WORD_LENGTH,
    MIN_WORD_LENGTH,
    create_word_list_json,
    get_target_sample_size,
    normalize_brrrdle_words,
    select_curated_answers,
    write_brrrdle_artifacts,
)


def test_normalize_brrrdle_words_filters_to_unique_lowercase_ascii_words_by_length():
    words = [
        "aa",
        "abc",
        "apple",
        "Apple",
        "apple",
        "café",
        "a",
        "with-hyphen",
        "abcdefghijklmnopqrstuvwxyzabcdefghi",
        "abcdefghijklmnopqrstuvwxyzabcdefghij",
    ]

    grouped_words = normalize_brrrdle_words(words)

    assert grouped_words[2] == ["aa"]
    assert grouped_words[3] == ["abc"]
    assert grouped_words[5] == ["apple"]
    assert grouped_words[35] == ["abcdefghijklmnopqrstuvwxyzabcdefghi"]
    assert 36 not in grouped_words
    assert all(word == word.lower() and word.isascii() and word.isalpha() for words in grouped_words.values() for word in words)


def make_words(prefix: str, count: int, length: int = 5) -> list[str]:
    suffix_length = length - len(prefix)
    return [
        prefix + "".join(suffix)
        for suffix in islice(product("abcdefghijklmnopqrstuvwxyz", repeat=suffix_length), count)
    ]


def test_get_target_sample_size_uses_spec_formula_and_caps():
    assert get_target_sample_size(999) == 999
    assert get_target_sample_size(1000) == 2000
    assert get_target_sample_size(10000) == 2200
    assert get_target_sample_size(200000) == 8000


def test_create_word_list_json_uses_full_sorted_list_for_small_answer_sets():
    generated_at = datetime(2026, 5, 27, 18, 0, tzinfo=timezone.utc)
    valid_guesses = ["aa", "ab"]

    payload = create_word_list_json(valid_guesses, 2, generated_at)

    assert payload["metadata"]["curation"] == {
        "method": CURATION_METHOD,
        "seed": 44,
        "target_sample_size": 2,
        "curation_date": "2026-05-27T18:00:00Z",
        "note": CURATION_NOTE,
    }
    assert payload["answers"] == valid_guesses
    assert payload["validGuesses"] == valid_guesses


def test_select_curated_answers_is_deterministic_stratified_subset_for_large_lists():
    valid_words = make_words("a", 1500) + make_words("b", 1500)

    answers, target_sample_size = select_curated_answers(valid_words, 5)
    repeated_answers, repeated_target_sample_size = select_curated_answers(valid_words, 5)

    assert target_sample_size == max(2000, min(8000, int(math.sqrt(len(valid_words)) * 22)))
    assert repeated_target_sample_size == target_sample_size
    assert answers == repeated_answers
    assert len(answers) == target_sample_size
    assert set(answers) <= set(valid_words)
    assert sum(1 for word in answers if word.startswith("a")) == 1000
    assert sum(1 for word in answers if word.startswith("b")) == 1000


def test_write_brrrdle_artifacts_outputs_primary_length_files_manifest_readme_and_legacy_files(tmp_path):
    source_path = tmp_path / "merged_valid_words.txt"
    dictionary_path = tmp_path / "merged_valid_dict.json"
    output_dir = tmp_path / "brrrdle"
    dictionary_metadata = {
        "aa": {"definition": "a rough basaltic lava"},
        "abc": {"definition": ""},
        "apple": {"definition": " a fruit "},
    }

    metadata = write_brrrdle_artifacts(
        words=["aa", "abc", "apple", "berry", "abcdef", "abcdefghijklmnopqrstuvwxyzabcdefghi"],
        output_dir=output_dir,
        source_path=source_path,
        dictionary_metadata=dictionary_metadata,
        dictionary_source_path=dictionary_path,
        release_date="2026-05-24",
        generated_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
    )

    primary_files = [f"words_length_{word_length}.json" for word_length in range(MIN_WORD_LENGTH, MAX_WORD_LENGTH + 1)]
    assert metadata["schema_version"] == "2.0"
    assert metadata["primary_files"] == primary_files
    assert metadata["per_length_counts"] == {
        str(word_length): (1 if word_length in {2, 3, 6, 35} else 2 if word_length == 5 else 0)
        for word_length in range(MIN_WORD_LENGTH, MAX_WORD_LENGTH + 1)
    }
    assert metadata["total_word_count"] == 6
    assert metadata["legacy_compatibility_files"] == ["brrrdle_words.txt", "brrrdle_words.json"]

    generated_primary_files = [
        f"words_length_{word_length}.json"
        for word_length in range(MIN_WORD_LENGTH, MAX_WORD_LENGTH + 1)
        if (output_dir / f"words_length_{word_length}.json").is_file()
    ]
    assert generated_primary_files == primary_files
    length_2_payload = json.loads((output_dir / "words_length_2.json").read_text())
    assert length_2_payload["metadata"]["curation"] == {
        "method": CURATION_METHOD,
        "seed": 44,
        "target_sample_size": 1,
        "curation_date": "2026-05-24T00:00:00Z",
        "note": CURATION_NOTE,
    }
    assert length_2_payload["answers"] == ["aa"]
    assert length_2_payload["validGuesses"] == ["aa"]

    length_3_payload = json.loads((output_dir / "words_length_3.json").read_text())
    assert length_3_payload["answers"] == ["abc"]
    assert length_3_payload["validGuesses"] == ["abc"]

    length_5_payload = json.loads((output_dir / "words_length_5.json").read_text())
    assert length_5_payload["metadata"]["curation"]["seed"] == 47
    assert length_5_payload["answers"] == ["apple", "berry"]
    assert length_5_payload["validGuesses"] == ["apple", "berry"]

    assert (output_dir / "brrrdle_words.txt").read_text() == "apple\nberry\n"
    legacy_payload = json.loads((output_dir / "brrrdle_words.json").read_text())
    assert legacy_payload["metadata"]["schema_version"] == "2.0"
    assert legacy_payload["words"] == ["apple", "berry"]

    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["schema_version"] == "2.0"
    assert manifest["primary_files"] == primary_files
    assert manifest["files"] == [
        *primary_files,
        "brrrdle_words.txt",
        "brrrdle_words.json",
        "manifest.json",
        "README.md",
    ]

    readme = (output_dir / "README.md").read_text()
    assert "words_length_{N}.json" in readme
    assert "from 2 through 35 letters" in readme
    assert "metadata.curation" in readme
    assert "answers" in readme
    assert "validGuesses" in readme
    assert "word arrays" in readme
    assert "stratified_quality_score_v1" in readme
    assert "transition period" in readme
