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
from collections import Counter
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    VALID_WORDS_FILE,
    INVALID_WORDS_FILE,
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



def load_existing_overall_stats() -> dict:
    """Load existing blog-facing overall stats when available."""
    if not OVERALL_STATS_FILE.exists():
        return {}
    try:
        with open(OVERALL_STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"Could not read existing overall stats: {exc}")
        return {}


def count_invalid_entries():
    """Count invalid entries only when the source file is available."""
    if not INVALID_WORDS_FILE.exists():
        return "not recorded"
    try:
        with open(INVALID_WORDS_FILE, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except OSError as exc:
        logger.warning(f"Could not count invalid entries: {exc}")
        return "not recorded"


def load_update_stats(release_dir: Path) -> dict:
    """Load machine-readable update stats when the pipeline created them."""
    stats_file = release_dir / "update_stats.json"
    if not stats_file.exists():
        return {}
    try:
        with open(stats_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"Could not load update stats: {exc}")
        return {}


def append_updates_log(stats: dict, release_date: str, release_dir: Path):
    """Update the blog-facing history log without inventing missing values."""
    UPDATES_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "update_number",
        "date",
        "timestamp",
        "total_valid_words_after",
        "words_added_today",
        "words_promoted_today",
        "new_words_from_rss",
        "new_words_from_wordnik",
        "new_words_from_invalid_list",
        "new_words_from_manual",
        "api_calls_mw",
        "api_calls_wordnik",
        "execution_duration_seconds",
        "blog_post_url",
        "notes",
    ]
    rows = []
    if UPDATES_LOG_FILE.exists():
        with open(UPDATES_LOG_FILE, "r", encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

    rows = [row for row in rows if row.get("date") != release_date]
    next_update = max([int(row.get("update_number") or 0) for row in rows] or [0]) + 1
    update_stats = load_update_stats(release_dir)
    promoted_words = update_stats.get("promoted_words")
    new_words = update_stats.get("new_words")
    promoted_count = len(promoted_words) if isinstance(promoted_words, list) else "not recorded"
    new_words_count = len(new_words) if isinstance(new_words, list) else "not recorded"
    if isinstance(promoted_count, int) and isinstance(new_words_count, int):
        words_added_today = promoted_count + new_words_count
    else:
        words_added_today = "not recorded"

    rows.append({
        "update_number": next_update,
        "date": release_date,
        "timestamp": stats.get("last_updated", release_date),
        "total_valid_words_after": stats.get("total_valid_words", "not recorded"),
        "words_added_today": words_added_today,
        "words_promoted_today": promoted_count,
        "new_words_from_rss": "not recorded",
        "new_words_from_wordnik": "not recorded",
        "new_words_from_invalid_list": promoted_count,
        "new_words_from_manual": "not recorded",
        "api_calls_mw": "not recorded",
        "api_calls_wordnik": "not recorded",
        "execution_duration_seconds": "not recorded",
        "blog_post_url": f"/english-openlist/daily-updates/{release_date}-daily-update/",
        "notes": "Missing metrics are not recorded rather than reconstructed.",
    })

    rows.sort(key=lambda row: row.get("date", ""))
    with open(UPDATES_LOG_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"Updated updates_log.csv for {release_date}")

def update_overall_stats(words: list[str], release_date: str) -> dict:
    """Update overall_stats.json with latest totals and distributions."""
    total = len(words)
    length_dist = compute_word_length_distribution(words)
    letter_dist = compute_starting_letter_distribution(words)

    existing_stats = load_existing_overall_stats()
    stats = {
        "last_updated": release_date,
        "total_valid_words": total,
        "total_invalid_entries": count_invalid_entries(),
        "total_updates": int(existing_stats.get("total_updates") or 0) + 1,
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
    stats = update_overall_stats(words, release_date)

    # Write daily CSVs
    write_distribution_csvs(length_dist, letter_dist, release_dir)

    # Update blog-facing history log
    append_updates_log(stats, release_date, release_dir)

    # Simple summary
    print(f"\nTotal valid words: {len(words):,}")
    print(f"Word lengths: {min(length_dist.keys())} - {max(length_dist.keys())}")
    print(f"Starting letters: {len(letter_dist)} unique")
    print(f"\nFiles written to: {release_dir}")
    print("Statistics generation complete!")
    return 0


if __name__ == "__main__":
    exit(main())
