import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.generate_brrrdle_artifacts import (
    MAX_WORD_LENGTH,
    MIN_WORD_LENGTH,
    normalize_brrrdle_words,
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
    assert json.loads((output_dir / "words_length_2.json").read_text()) == [
        {"word": "aa", "definition": "a rough basaltic lava"}
    ]
    assert json.loads((output_dir / "words_length_3.json").read_text()) == [{"word": "abc"}]
    assert json.loads((output_dir / "words_length_5.json").read_text()) == [
        {"word": "apple", "definition": "a fruit"},
        {"word": "berry"},
    ]

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
    assert "definition" in readme
    assert "transition period" in readme
