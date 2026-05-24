import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.generate_brrrdle_artifacts import normalize_brrrdle_words, write_brrrdle_artifacts


def test_normalize_brrrdle_words_filters_to_unique_lowercase_ascii_five_letter_words():
    words = ["apple", "Apple", "apple", "café", "berry", "abcd", "abcdef", "robin", "with-hyphen"]

    assert normalize_brrrdle_words(words) == ["apple", "berry", "robin"]


def test_write_brrrdle_artifacts_outputs_words_json_manifest_and_readme(tmp_path):
    source_path = tmp_path / "merged_valid_words.txt"
    source_path.write_text("apple\nberry\nabcdef\n")
    output_dir = tmp_path / "brrrdle"

    metadata = write_brrrdle_artifacts(
        words=["apple", "berry", "abcdef"],
        output_dir=output_dir,
        source_path=source_path,
        release_date="2026-05-24",
        generated_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
    )

    assert metadata["word_count"] == 2
    assert (output_dir / "brrrdle_words.txt").read_text() == "apple\nberry\n"

    payload = json.loads((output_dir / "brrrdle_words.json").read_text())
    assert payload["metadata"]["release_date"] == "2026-05-24"
    assert payload["words"] == ["apple", "berry"]

    manifest = json.loads((output_dir / "manifest.json").read_text())
    assert manifest["files"] == [
        "brrrdle_words.txt",
        "brrrdle_words.json",
        "manifest.json",
        "README.md",
    ]
    assert "Hugging Face" in (output_dir / "README.md").read_text()
