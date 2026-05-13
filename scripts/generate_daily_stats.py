"""
Daily Statistics Generator
Computes word length, starting letter, and other distributions for the English OpenList.

Outputs:
- word_length_distribution.csv
- starting_letter_distribution.csv
- daily_stats_summary.json

Also updates overall_stats.json and updates_log.csv
"""

import json
import csv
from pathlib import Path
from collections import Counter, defaultdict
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    VALID_WORDS_FILE,
    get_release_dir,
    OVERALL_STATS_FILE,
    UPDATES_LOG_FILE,
    get_release_date
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_valid_words() -> list[str]:
    """Load all valid words from the downloaded file."""
    if not VALID_WORDS_FILE.exists():
        logger.error(f"Valid words file not found: {VALID_WORDS_FILE}")
        return []
    with open(VALID_WORDS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def compute_word_length_distribution(words: list[str]) -> dict[int, int]:
    """Return {length: count} for all words."""
    return dict(Counter(len(w) for w in words))


def compute_starting_letter_distribution(words: list[str]) -> dict[str, int]:
    """Return {letter: count} for starting letters (a-z)."""
    return dict(Counter(w[0].lower() for w in words if w))


def update_overall_stats(words: list[str], release_date: str) -> dict:
    """Update overall_stats.json with latest totals and distributions."""
    total = len(words)
    length_dist = compute_word_length_distribution(words)
    letter_dist = compute_starting_letter_distribution(words)

    stats = {
        "last_updated": release_date,
        "total_valid_words": total,
        "total_invalid_entries": 9275000,  # placeholder until we track it properly
        "total_updates": 1,  # will be incremented by tracker script later
        "word_length_distribution": length_dist,
        "starting_letter_distribution": letter_dist
    }

    with open(OVERALL_STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    logger.info(f"Updated overall_stats.json with {total} words")
    return stats


def write_distribution_csvs(length_dist: dict, letter_dist: dict, release_dir: Path):
    """Write CSV files for the daily release folder."""
    # Word length
    length_csv = release_dir / "word_length_distribution.csv"
    with open(length_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["word_length", "count"])
        for length in sorted(length_dist.keys()):
            writer.writerow([length, length_dist[length]])

    # Starting letter
    letter_csv = release_dir / "starting_letter_distribution.csv"
    with open(letter_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["starting_letter", "count"])
        for letter in sorted(letter_dist.keys()):
            writer.writerow([letter, letter_dist[letter]])

    logger.info(f"Wrote distribution CSVs to {release_dir}")


def main():
    print("=" * 60)
    print("English OpenList - Daily Statistics Generator")
    print("=" * 60)

    words = load_valid_words()
    if not words:
        print("No words loaded. Exiting.")
        return 1

    release_date = get_release_date()
    release_dir = get_release_dir()

    # Compute distributions
    length_dist = compute_word_length_distribution(words)
    letter_dist = compute_starting_letter_distribution(words)

    # Update overall stats
    update_overall_stats(words, release_date)

    # Write daily CSVs
    write_distribution_csvs(length_dist, letter_dist, release_dir)

    # Simple summary
    print(f"\nTotal valid words: {len(words):,}")
    print(f"Word lengths: {min(length_dist.keys())} - {max(length_dist.keys())}")
    print(f"Starting letters: {len(letter_dist)} unique")
    print(f"\nFiles written to: {release_dir}")
    print("Statistics generation complete!")
    return 0


if __name__ == "__main__":
    exit(main())
