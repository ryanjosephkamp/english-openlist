"""
Generate Brrrdle-compatible word list artifacts from English OpenList data.

Brrrdle artifacts are generated as transient release outputs and are intended
for upload to Hugging Face, not for committed repository data folders.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VALID_DICT_FILE, VALID_WORDS_FILE, get_release_date, get_release_dir

logger = logging.getLogger(__name__)

MIN_WORD_LENGTH = 2
MAX_WORD_LENGTH = 35
LEGACY_WORD_LENGTH = 5
BRRRDLE_SCHEMA_VERSION = "2.0"
ARTIFACT_WORDS_FILENAME = "brrrdle_words.txt"
ARTIFACT_JSON_FILENAME = "brrrdle_words.json"
ARTIFACT_MANIFEST_FILENAME = "manifest.json"
ARTIFACT_README_FILENAME = "README.md"


def supported_word_lengths() -> range:
    """Return the supported Brrrdle word length range."""
    return range(MIN_WORD_LENGTH, MAX_WORD_LENGTH + 1)


def length_artifact_filename(word_length: int) -> str:
    """Return the primary JSON artifact filename for a word length."""
    return f"words_length_{word_length}.json"


def normalize_brrrdle_words(
    words: Iterable[str],
    min_length: int = MIN_WORD_LENGTH,
    max_length: int = MAX_WORD_LENGTH,
) -> dict[int, list[str]]:
    """Return sorted, unique, lowercase alphabetic words grouped by supported length."""
    grouped_words: dict[int, set[str]] = {word_length: set() for word_length in range(min_length, max_length + 1)}
    for word in words:
        normalized_word = word.strip()
        word_length = len(normalized_word)
        if (
            normalized_word
            and min_length <= word_length <= max_length
            and normalized_word.isascii()
            and normalized_word.isalpha()
            and normalized_word.islower()
        ):
            grouped_words[word_length].add(normalized_word)
    return {word_length: sorted(grouped_words[word_length]) for word_length in grouped_words}


def load_words(path: Path) -> list[str]:
    """Load newline-delimited words from a text file."""
    with open(path, "r", encoding="utf-8") as word_file:
        return [line.strip() for line in word_file if line.strip()]


def load_dictionary_metadata(path: Path) -> dict[str, dict[str, Any]]:
    """Load valid dictionary metadata when available."""
    if not path.exists():
        logger.warning("Dictionary metadata not found: %s", path)
        return {}

    with open(path, "r", encoding="utf-8") as dictionary_file:
        payload = json.load(dictionary_file)

    if not isinstance(payload, dict):
        logger.warning("Dictionary metadata must be a JSON object: %s", path)
        return {}

    return {word: metadata for word, metadata in payload.items() if isinstance(word, str) and isinstance(metadata, dict)}


def build_word_entry(word: str, dictionary_metadata: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Build a Brrrdle word entry with an optional top-level definition."""
    entry = {"word": word}
    definition = dictionary_metadata.get(word, {}).get("definition")
    if isinstance(definition, str) and definition.strip():
        entry["definition"] = definition.strip()
    return entry


def write_brrrdle_artifacts(
    words: Iterable[str],
    output_dir: Path,
    source_path: Path,
    dictionary_metadata: dict[str, dict[str, Any]] | None = None,
    dictionary_source_path: Path | None = None,
    release_date: str | None = None,
    generated_at: datetime | None = None,
) -> dict:
    """Write Brrrdle artifacts and return their manifest metadata."""
    output_dir.mkdir(parents=True, exist_ok=True)
    release_date = release_date or get_release_date()
    generated_at = generated_at or datetime.now(timezone.utc)
    generated_at_iso = generated_at.isoformat()
    dictionary_metadata = dictionary_metadata or {}
    grouped_words = normalize_brrrdle_words(words)
    primary_files = [length_artifact_filename(word_length) for word_length in supported_word_lengths()]
    per_length_counts = {str(word_length): len(grouped_words[word_length]) for word_length in supported_word_lengths()}
    legacy_words = grouped_words[LEGACY_WORD_LENGTH]

    metadata = {
        "dataset": "english-openlist-brrrdle",
        "schema_version": BRRRDLE_SCHEMA_VERSION,
        "release_date": release_date,
        "generated_at": generated_at_iso,
        "source_file": str(source_path),
        "dictionary_source_file": str(dictionary_source_path) if dictionary_source_path else None,
        "supported_word_lengths": {
            "min": MIN_WORD_LENGTH,
            "max": MAX_WORD_LENGTH,
        },
        "total_word_count": sum(per_length_counts.values()),
        "per_length_counts": per_length_counts,
        "primary_files": primary_files,
        "legacy_compatibility_files": [
            ARTIFACT_WORDS_FILENAME,
            ARTIFACT_JSON_FILENAME,
        ],
        "files": [
            *primary_files,
            ARTIFACT_WORDS_FILENAME,
            ARTIFACT_JSON_FILENAME,
            ARTIFACT_MANIFEST_FILENAME,
            ARTIFACT_README_FILENAME,
        ],
    }

    for word_length, brrrdle_words in grouped_words.items():
        length_path = output_dir / length_artifact_filename(word_length)
        length_payload = [build_word_entry(word, dictionary_metadata) for word in brrrdle_words]
        length_path.write_text(json.dumps(length_payload, indent=2) + "\n", encoding="utf-8")

    words_path = output_dir / ARTIFACT_WORDS_FILENAME
    words_path.write_text("".join(f"{word}\n" for word in legacy_words), encoding="utf-8")

    json_path = output_dir / ARTIFACT_JSON_FILENAME
    json_path.write_text(
        json.dumps({"metadata": metadata, "words": legacy_words}, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest_path = output_dir / ARTIFACT_MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    readme_path = output_dir / ARTIFACT_README_FILENAME
    readme_path.write_text(
        "# English OpenList Brrrdle Artifacts\n\n"
        f"Generated on `{generated_at_iso}` for release `{release_date}`.\n\n"
        f"This folder contains primary JSON artifacts for lowercase ASCII words "
        f"from {MIN_WORD_LENGTH} through {MAX_WORD_LENGTH} letters, derived from English OpenList.\n\n"
        "## Primary files\n\n"
        "`words_length_{N}.json` files are the primary Brrrdle artifacts. "
        "Each file is a JSON array of objects with a `word` field. "
        "A `definition` field is included only when a non-empty top-level definition "
        "is available from the valid dictionary metadata.\n\n"
        "## Transitional compatibility files\n\n"
        "`brrrdle_words.txt` and `brrrdle_words.json` are length-5 compatibility outputs "
        "kept for one transition period and will be removed in a future major update.\n\n"
        "These generated files are published to Hugging Face dataset paths, "
        "not committed as repository `latest/` or `data/brrrdle/` folders.\n",
        encoding="utf-8",
    )

    logger.info("Generated %s Brrrdle words in %s", metadata["total_word_count"], output_dir)
    return metadata


def generate_brrrdle_artifacts(
    input_path: Path = VALID_WORDS_FILE,
    dictionary_path: Path = VALID_DICT_FILE,
    output_dir: Path | None = None,
    release_date: str | None = None,
) -> dict:
    """Generate Brrrdle artifacts from a newline-delimited valid word list."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input word list not found: {input_path}")

    output_dir = output_dir or (get_release_dir() / "brrrdle")
    words = load_words(input_path)
    dictionary_metadata = load_dictionary_metadata(dictionary_path)
    return write_brrrdle_artifacts(
        words=words,
        output_dir=output_dir,
        source_path=input_path,
        dictionary_metadata=dictionary_metadata,
        dictionary_source_path=dictionary_path,
        release_date=release_date,
    )


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate Brrrdle word list artifacts")
    parser.add_argument("--input", type=Path, default=VALID_WORDS_FILE, help="Input valid word list")
    parser.add_argument("--dictionary", type=Path, default=VALID_DICT_FILE, help="Input valid dictionary metadata")
    parser.add_argument("--output-dir", type=Path, help="Output directory for generated artifacts")
    parser.add_argument("--date", type=str, help="Release date for manifest metadata")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    metadata = generate_brrrdle_artifacts(
        input_path=args.input,
        dictionary_path=args.dictionary,
        output_dir=args.output_dir,
        release_date=args.date,
    )
    print(f"Generated {metadata['total_word_count']} Brrrdle words")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
