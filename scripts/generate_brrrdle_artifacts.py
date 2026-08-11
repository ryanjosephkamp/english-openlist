"""
Generate Brrrdle-compatible word list artifacts from English OpenList data.

Brrrdle artifacts are generated as transient release outputs and are intended
for upload to Hugging Face, not for committed repository data folders.
"""

from __future__ import annotations

import argparse
import math
import json
import logging
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

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
CURATION_METHOD = "stratified_quality_score_v1"
CURATION_NOTE = (
    "Stratified by starting letter + quality score "
    "(frequency 0.45, positional 0.30, vowel balance 0.15, uniqueness 0.10)"
)
VOWELS = frozenset("aeiou")


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


def get_target_sample_size(total_valid_guesses: int) -> int:
    """Return the spec-defined dynamic answer target for a valid guess count."""
    if total_valid_guesses < 1000:
        return total_valid_guesses
    target = int(math.sqrt(total_valid_guesses) * 22)
    return max(2000, min(8000, target))


def format_utc_z(timestamp: datetime) -> str:
    """Return an ISO-8601 UTC timestamp with a Z suffix."""
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_curation_metadata(length: int, target_sample_size: int, curation_date: datetime) -> dict[str, Any]:
    """Build the required Brrrdle answers curation metadata block."""
    return {
        "method": CURATION_METHOD,
        "seed": 42 + length,
        "target_sample_size": target_sample_size,
        "curation_date": format_utc_z(curation_date),
        "note": CURATION_NOTE,
    }


def build_letter_frequency(words: Sequence[str]) -> dict[str, float]:
    """Return corpus-wide letter frequencies normalized to [0, 1]."""
    letter_counts = Counter("".join(words))
    total_letters = sum(letter_counts.values())
    if not total_letters:
        return {}
    return {letter: count / total_letters for letter, count in letter_counts.items()}


def build_positional_frequency(words: Sequence[str], length: int) -> list[dict[str, float]]:
    """Return per-position letter frequencies normalized to [0, 1]."""
    positional_counts = [Counter() for _ in range(length)]
    for word in words:
        for index, letter in enumerate(word):
            positional_counts[index][letter] += 1

    total_words = len(words)
    if not total_words:
        return [{} for _ in range(length)]
    return [
        {letter: count / total_words for letter, count in position_counts.items()}
        for position_counts in positional_counts
    ]


def get_vowel_ratio(word: str) -> float:
    """Return the fraction of letters in a word that are vowels."""
    if not word:
        return 0.0
    return sum(1 for letter in word if letter in VOWELS) / len(word)


def letter_frequency_similarity(word: str, corpus_letter_frequency: dict[str, float]) -> float:
    """Score how closely a word's letter distribution matches the corpus."""
    if not word:
        return 0.0

    word_counts = Counter(word)
    word_frequency = {letter: count / len(word) for letter, count in word_counts.items()}
    letters = set(corpus_letter_frequency) | set(word_frequency)
    distance = sum(abs(word_frequency.get(letter, 0.0) - corpus_letter_frequency.get(letter, 0.0)) for letter in letters) / 2
    return max(0.0, min(1.0, 1.0 - distance))


def positional_match_score(word: str, positional_frequency: Sequence[dict[str, float]]) -> float:
    """Score how common each letter is in its position for this length."""
    if not word:
        return 0.0
    return sum(positional_frequency[index].get(letter, 0.0) for index, letter in enumerate(word)) / len(word)


def vowel_consonant_balance_score(word: str, corpus_vowel_ratio: float) -> float:
    """Score how closely a word's vowel ratio matches the corpus vowel ratio."""
    return max(0.0, min(1.0, 1.0 - abs(get_vowel_ratio(word) - corpus_vowel_ratio)))


def uniqueness_score(word: str) -> float:
    """Score the fraction of unique letters in a word."""
    if not word:
        return 0.0
    return len(set(word)) / len(word)


def quality_score(
    word: str,
    corpus_letter_frequency: dict[str, float],
    positional_frequency: Sequence[dict[str, float]],
    corpus_vowel_ratio: float,
) -> float:
    """Return the approved weighted quality score for a Brrrdle answer."""
    return (
        0.45 * letter_frequency_similarity(word, corpus_letter_frequency)
        + 0.30 * positional_match_score(word, positional_frequency)
        + 0.15 * vowel_consonant_balance_score(word, corpus_vowel_ratio)
        + 0.10 * uniqueness_score(word)
    )


def allocate_bucket_targets(buckets: dict[str, list[str]], target_sample_size: int, total_valid_guesses: int) -> dict[str, int]:
    """Allocate a deterministic proportional answer count to each starting-letter bucket."""
    bucket_targets: dict[str, int] = {}
    fractional_remainders: list[tuple[float, str]] = []

    for letter in sorted(buckets):
        exact_target = (len(buckets[letter]) / total_valid_guesses) * target_sample_size
        bucket_target = min(len(buckets[letter]), int(exact_target))
        bucket_targets[letter] = bucket_target
        fractional_remainders.append((exact_target - bucket_target, letter))

    remaining = target_sample_size - sum(bucket_targets.values())
    for _, letter in sorted(fractional_remainders, key=lambda item: (-item[0], item[1])):
        if remaining <= 0:
            break
        if bucket_targets[letter] < len(buckets[letter]):
            bucket_targets[letter] += 1
            remaining -= 1

    while remaining > 0:
        progressed = False
        for letter in sorted(buckets):
            if bucket_targets[letter] < len(buckets[letter]):
                bucket_targets[letter] += 1
                remaining -= 1
                progressed = True
                if remaining == 0:
                    break
        if not progressed:
            break

    return bucket_targets


def select_curated_answers(valid_words: list[str], length: int) -> tuple[list[str], int]:
    """Select the spec-defined curated answer subset from the complete valid guesses."""
    target_sample_size = get_target_sample_size(len(valid_words))
    if len(valid_words) < 1000:
        return valid_words, target_sample_size

    rng = random.Random(42 + length)
    corpus_letter_frequency = build_letter_frequency(valid_words)
    positional_frequency = build_positional_frequency(valid_words, length)
    corpus_vowel_ratio = sum(get_vowel_ratio(word) for word in valid_words) / len(valid_words)
    buckets: dict[str, list[str]] = defaultdict(list)
    for word in valid_words:
        buckets[word[0]].append(word)

    bucket_targets = allocate_bucket_targets(buckets, target_sample_size, len(valid_words))
    selected_answers: list[str] = []

    for letter in sorted(buckets):
        words_with_tiebreakers = [(word, rng.random()) for word in buckets[letter]]
        ranked_bucket = sorted(
            words_with_tiebreakers,
            key=lambda item: (
                -quality_score(item[0], corpus_letter_frequency, positional_frequency, corpus_vowel_ratio),
                item[1],
                item[0],
            ),
        )
        selected_answers.extend(word for word, _ in ranked_bucket[: bucket_targets[letter]])

    return sorted(selected_answers), target_sample_size


def create_word_list_json(valid_guesses: list[str], length: int, generated_at: datetime) -> dict[str, Any]:
    """Build the per-length Brrrdle JSON payload with curated answers and full valid guesses."""
    answer_words, target_sample_size = select_curated_answers(valid_guesses, length)
    return {
        "metadata": {
            "curation": build_curation_metadata(length, target_sample_size, generated_at),
        },
        "answers": answer_words,
        "validGuesses": valid_guesses,
    }


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
        word_list_payload = create_word_list_json(brrrdle_words, word_length, generated_at)
        length_path.write_text(json.dumps(word_list_payload, indent=2) + "\n", encoding="utf-8")

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
        "Each file includes `metadata.curation`, curated `answers`, and complete "
        "`validGuesses` word arrays. `answers` are generated with the "
        "`stratified_quality_score_v1` method; `validGuesses` remains the full "
        "per-length list.\n\n"
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
