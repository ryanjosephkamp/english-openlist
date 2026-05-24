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
from typing import Iterable

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VALID_WORDS_FILE, get_release_date, get_release_dir

logger = logging.getLogger(__name__)

DEFAULT_WORD_LENGTH = 5
ARTIFACT_WORDS_FILENAME = "brrrdle_words.txt"
ARTIFACT_JSON_FILENAME = "brrrdle_words.json"
ARTIFACT_MANIFEST_FILENAME = "manifest.json"
ARTIFACT_README_FILENAME = "README.md"


def normalize_brrrdle_words(words: Iterable[str], word_length: int = DEFAULT_WORD_LENGTH) -> list[str]:
    """Return sorted, unique, lowercase alphabetic words matching Brrrdle length."""
    normalized_words = set()
    for word in words:
        normalized_word = word.strip()
        if (
            normalized_word
            and len(normalized_word) == word_length
            and normalized_word.isascii()
            and normalized_word.isalpha()
            and normalized_word.islower()
        ):
            normalized_words.add(normalized_word)
    return sorted(normalized_words)


def load_words(path: Path) -> list[str]:
    """Load newline-delimited words from a text file."""
    with open(path, "r", encoding="utf-8") as word_file:
        return [line.strip() for line in word_file if line.strip()]


def write_brrrdle_artifacts(
    words: Iterable[str],
    output_dir: Path,
    source_path: Path,
    release_date: str | None = None,
    generated_at: datetime | None = None,
    word_length: int = DEFAULT_WORD_LENGTH,
) -> dict:
    """Write Brrrdle artifacts and return their manifest metadata."""
    output_dir.mkdir(parents=True, exist_ok=True)
    release_date = release_date or get_release_date()
    generated_at = generated_at or datetime.now(timezone.utc)
    generated_at_iso = generated_at.isoformat()
    brrrdle_words = normalize_brrrdle_words(words, word_length=word_length)

    metadata = {
        "dataset": "english-openlist-brrrdle",
        "release_date": release_date,
        "generated_at": generated_at_iso,
        "source_file": str(source_path),
        "word_length": word_length,
        "word_count": len(brrrdle_words),
        "files": [
            ARTIFACT_WORDS_FILENAME,
            ARTIFACT_JSON_FILENAME,
            ARTIFACT_MANIFEST_FILENAME,
            ARTIFACT_README_FILENAME,
        ],
    }

    words_path = output_dir / ARTIFACT_WORDS_FILENAME
    words_path.write_text("".join(f"{word}\n" for word in brrrdle_words), encoding="utf-8")

    json_path = output_dir / ARTIFACT_JSON_FILENAME
    json_path.write_text(
        json.dumps({"metadata": metadata, "words": brrrdle_words}, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest_path = output_dir / ARTIFACT_MANIFEST_FILENAME
    manifest_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    readme_path = output_dir / ARTIFACT_README_FILENAME
    readme_path.write_text(
        "# English OpenList Brrrdle Artifacts\n\n"
        f"Generated on `{generated_at_iso}` for release `{release_date}`.\n\n"
        f"This folder contains {len(brrrdle_words):,} lowercase ASCII words "
        f"with exactly {word_length} letters, derived from English OpenList.\n\n"
        "These generated files are published to Hugging Face dataset paths, "
        "not committed as repository `latest/` or `data/brrrdle/` folders.\n",
        encoding="utf-8",
    )

    logger.info("Generated %s Brrrdle words in %s", len(brrrdle_words), output_dir)
    return metadata


def generate_brrrdle_artifacts(
    input_path: Path = VALID_WORDS_FILE,
    output_dir: Path | None = None,
    release_date: str | None = None,
    word_length: int = DEFAULT_WORD_LENGTH,
) -> dict:
    """Generate Brrrdle artifacts from a newline-delimited valid word list."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input word list not found: {input_path}")

    output_dir = output_dir or (get_release_dir() / "brrrdle")
    words = load_words(input_path)
    return write_brrrdle_artifacts(
        words=words,
        output_dir=output_dir,
        source_path=input_path,
        release_date=release_date,
        word_length=word_length,
    )


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Generate Brrrdle word list artifacts")
    parser.add_argument("--input", type=Path, default=VALID_WORDS_FILE, help="Input valid word list")
    parser.add_argument("--output-dir", type=Path, help="Output directory for generated artifacts")
    parser.add_argument("--date", type=str, help="Release date for manifest metadata")
    parser.add_argument("--word-length", type=int, default=DEFAULT_WORD_LENGTH, help="Required word length")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")

    metadata = generate_brrrdle_artifacts(
        input_path=args.input,
        output_dir=args.output_dir,
        release_date=args.date,
        word_length=args.word_length,
    )
    print(f"Generated {metadata['word_count']} Brrrdle words")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
