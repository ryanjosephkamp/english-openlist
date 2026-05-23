"""
Daily Blog Post Generator
Creates the daily automated blog post with interactive statistics charts.
"""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_release_date, BLOG_POSTS_DIR, OUTPUT_DIR, OVERALL_STATS_FILE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_json(path: Path, default):
    """Load JSON from path, returning default if the file is unavailable."""
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load %s: %s", path, exc)
        return default


def load_promoted_words(release_dir: Path) -> list[str]:
    """Load words promoted from invalid to valid during this release."""
    promoted_file = release_dir / "promoted_words.txt"
    if not promoted_file.exists():
        return []
    with open(promoted_file, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_distribution_csv(path: Path, key_field: str) -> dict[str, int]:
    """Load a two-column distribution CSV as a dictionary."""
    if not path.exists():
        return {}

    distribution: dict[str, int] = {}
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row.get(key_field)
            count = row.get("count")
            if key is None or count is None:
                continue
            distribution[str(key)] = int(count)
    return distribution


def html_safe_json(data) -> str:
    """Serialize JSON for safe embedding in a script tag."""
    return (
        json.dumps(data, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def build_chart_data(release_dir: Path, overall_stats: dict) -> dict:
    """Build ordered chart data from daily CSVs, falling back to overall stats."""
    length_dist = load_distribution_csv(
        release_dir / "word_length_distribution.csv",
        "word_length",
    ) or overall_stats.get("word_length_distribution", {})

    letter_dist = load_distribution_csv(
        release_dir / "starting_letter_distribution.csv",
        "starting_letter",
    ) or overall_stats.get("starting_letter_distribution", {})

    length_items = sorted((int(length), count) for length, count in length_dist.items())
    letters = [chr(code) for code in range(ord("a"), ord("z") + 1)]

    return {
        "wordLength": {
            "labels": [str(length) for length, _ in length_items],
            "values": [count for _, count in length_items],
        },
        "startingLetter": {
            "labels": [letter.upper() for letter in letters],
            "values": [int(letter_dist.get(letter, 0)) for letter in letters],
        },
    }


def format_words(words: list[str]) -> str:
    """Format words for a markdown code block."""
    return "\n".join(words) if words else ""


def generate_blog_post():
    release_date = get_release_date()
    release_dir = OUTPUT_DIR / release_date
    BLOG_POSTS_DIR.mkdir(parents=True, exist_ok=True)

    overall_stats = load_json(OVERALL_STATS_FILE, {})
    update_stats = load_json(release_dir / "update_stats.json", {})
    execution_summary = load_json(release_dir / "daily_execution_summary.json", {})
    promoted_words = update_stats.get("promoted_words") or load_promoted_words(release_dir)
    new_words = update_stats.get("new_words", [])
    chart_data = build_chart_data(release_dir, overall_stats)

    total_valid_words = overall_stats.get(
        "total_valid_words",
        update_stats.get("total_valid_after", 0),
    )
    total_invalid_entries = overall_stats.get(
        "total_invalid_entries",
        update_stats.get("total_invalid_after", 0),
    )
    words_added_today = len(new_words) + len(promoted_words)
    generated_at = datetime.now(timezone.utc)
    timestamp = generated_at.strftime("%Y-%m-%d %H:%M:%S")
    full_timestamp = generated_at.isoformat()

    api_health = execution_summary.get("api_health", {})
    words_by_source = execution_summary.get("words_by_source", {})
    mw_health = api_health.get("merriam_webster", {})
    wordnik_health = api_health.get("wordnik", {})

    promoted_section = ""
    if promoted_words:
        promoted_section = f"""
### Words Promoted Today

```text
{format_words(promoted_words)}
```
"""

    new_words_section = ""
    if new_words:
        new_words_section = f"""
### New Words Discovered Today

```text
{format_words(new_words)}
```
"""

    post_content = f"""---
layout: post
title: "Daily English OpenList Update - {release_date}"
date: {full_timestamp}
categories: [daily-updates]
tags: [daily, statistics, words]
---

# Daily English OpenList Update — {release_date}

**Generated automatically at {timestamp} UTC**

## Today's Results

- **Total words added today:** {words_added_today}
- **New words discovered today:** {len(new_words)}
- **Words promoted from invalid list:** {len(promoted_words)}
- **Total valid words now:** **{total_valid_words:,}**
- **Total invalid entries tracked:** {total_invalid_entries:,}
{new_words_section}{promoted_section}
## Interactive Statistics

### Starting Letter Distribution (full valid list)

<div class="daily-update-chart-container" style="position: relative; width: 100%; max-width: 900px; height: 420px; margin: 1.5rem auto;">
  <canvas id="dailyStartingLetterChart"></canvas>
</div>

### Word Length Distribution (full valid list)

<div class="daily-update-chart-container" style="position: relative; width: 100%; max-width: 900px; height: 420px; margin: 1.5rem auto;">
  <canvas id="dailyWordLengthChart"></canvas>
</div>

<script id="daily-chart-data" type="application/json">{html_safe_json(chart_data)}</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="{{{{ '/assets/js/daily-update-charts.js' | relative_url }}}}"></script>

## Execution Transparency

**API Health Check**
- Merriam-Webster API calls: {mw_health.get("calls_made", 0)} ({mw_health.get("success_rate", 0)}% success)
- Wordnik API calls: {wordnik_health.get("calls_made", 0)} ({wordnik_health.get("success_rate", 0)}% success)

**Words Discovered by Source**
- Merriam-Webster RSS / New Words: {words_by_source.get("merriam_webster_rss", 0) + words_by_source.get("merriam_webster_new_words", 0)}
- Wordnik Word of the Day: {words_by_source.get("wordnik_wotd", 0)}
- Invalid list validation: {words_by_source.get("invalid_list_validation", len(promoted_words))}
- Manual additions: {words_by_source.get("manual_additions", 0)}

## Release Files

- `starting_letter_distribution.csv` and `word_length_distribution.csv` — full-list distributions used for the charts above
- `CHANGELOG.md` — detailed process log
- `update_stats.json` — machine-readable update summary

*Generated automatically by the English OpenList daily pipeline.*
"""

    post_path = BLOG_POSTS_DIR / f"{release_date}-daily-update.md"
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(post_content)

    logger.info(f"Blog post created: {post_path}")
    return post_path


def main():
    print("Generating daily blog post...")
    post_path = generate_blog_post()
    print(f"Done: {post_path}")
    return 0


if __name__ == "__main__":
    exit(main())
