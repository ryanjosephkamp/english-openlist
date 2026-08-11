"""
Daily Blog Post Generator
Creates the daily automated blog post with honest statistics and optional charts.
"""

import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import BLOG_POSTS_DIR, OUTPUT_DIR, OVERALL_STATS_FILE, get_release_date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NOT_RECORDED = "not recorded"
UNAVAILABLE = "unavailable"


def load_json(path: Path, default: Any):
    """Load JSON from path, returning default if the file is unavailable."""
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load %s: %s", path, exc)
        return default


def load_lines(path: Path) -> list[str] | None:
    """Load stripped non-empty lines, or None when the file is unavailable."""
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except OSError as exc:
        logger.warning("Could not load %s: %s", path, exc)
        return None


def load_promoted_words(release_dir: Path) -> list[str] | None:
    """Load words promoted from invalid to valid during this release."""
    return load_lines(release_dir / "promoted_words.txt")


def load_distribution_csv(path: Path, key_field: str) -> dict[str, int] | None:
    """Load a two-column distribution CSV as a dictionary."""
    if not path.exists():
        return None

    distribution: dict[str, int] = {}
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = row.get(key_field)
                count = row.get("count")
                if key is None or count is None:
                    continue
                distribution[str(key)] = int(count)
    except (OSError, ValueError) as exc:
        logger.warning("Could not load distribution %s: %s", path, exc)
        return None

    return distribution or None


def html_safe_json(data: Any) -> str:
    """Serialize JSON for safe embedding in a script tag."""
    return (
        json.dumps(data, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def build_chart_data(release_dir: Path) -> dict[str, dict[str, list[int | str]]] | None:
    """Build ordered chart data when release distribution CSVs are available."""
    length_dist = load_distribution_csv(
        release_dir / "word_length_distribution.csv",
        "word_length",
    )
    letter_dist = load_distribution_csv(
        release_dir / "starting_letter_distribution.csv",
        "starting_letter",
    )

    if not length_dist or not letter_dist:
        return None

    try:
        length_items = sorted((int(length), count) for length, count in length_dist.items())
    except ValueError as exc:
        logger.warning("Could not parse word length distribution: %s", exc)
        return None

    letters = [chr(code) for code in range(ord("a"), ord("z") + 1)]
    letter_values = [int(letter_dist.get(letter, 0)) for letter in letters]
    if not length_items or not any(letter_values):
        return None

    return {
        "wordLength": {
            "labels": [str(length) for length, _ in length_items],
            "values": [count for _, count in length_items],
        },
        "startingLetter": {
            "labels": [letter.upper() for letter in letters],
            "values": letter_values,
        },
    }


def format_words(words: list[str] | None) -> str:
    """Format words for a markdown code block."""
    return "\n".join(words or [])


def display_count(value: Any) -> str:
    """Format recorded numeric values while preserving honest missing labels."""
    if value in (None, ""):
        return NOT_RECORDED
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def list_from_stats(update_stats: dict[str, Any], key: str) -> list[str] | None:
    """Return a list from update_stats only when the key was actually recorded."""
    if key not in update_stats:
        return None
    value = update_stats.get(key)
    return value if isinstance(value, list) else None


def value_from_sources(*values: Any) -> Any:
    """Return the first recorded value from a sequence."""
    for value in values:
        if value not in (None, ""):
            return value
    return None


def sum_recorded_values(*values: Any) -> Any:
    """Sum numeric recorded values, or report not recorded when none exist."""
    recorded = [value for value in values if isinstance(value, int)]
    if not recorded:
        return None
    return sum(recorded)


def render_words_section(title: str, words: list[str] | None) -> str:
    """Render an optional word list section."""
    if not words:
        return ""
    return f"""
### {title}

```text
{format_words(words)}
```
"""


def render_charts_section(chart_data: dict[str, dict[str, list[int | str]]] | None) -> str:
    """Render chart markup only when valid chart data exists."""
    if not chart_data:
        return """
## Statistics Charts

Chart data was unavailable for this automated run, so no charts are shown for this post.
"""

    return f"""
## Interactive Statistics

### Starting Letter Distribution

<div class="daily-update-chart-container">
  <canvas id="dailyStartingLetterChart" aria-label="Starting letter distribution chart" role="img"></canvas>
  <p class="daily-update-chart-fallback">Chart data is available as structured JSON in this post.</p>
</div>

### Word Length Distribution

<div class="daily-update-chart-container">
  <canvas id="dailyWordLengthChart" aria-label="Word length distribution chart" role="img"></canvas>
  <p class="daily-update-chart-fallback">Chart data is available as structured JSON in this post.</p>
</div>

<script id="daily-chart-data" type="application/json">{html_safe_json(chart_data)}</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="{{{{ '/assets/js/daily-update-charts.js' | relative_url }}}}"></script>
"""


def render_execution_summary(execution_summary: dict[str, Any], promoted_words: list[str] | None) -> str:
    """Render execution transparency with honest missing values."""
    api_health = execution_summary.get("api_health", {}) if execution_summary else {}
    words_by_source = execution_summary.get("words_by_source", {}) if execution_summary else {}
    mw_health = api_health.get("merriam_webster", {})
    wordnik_health = api_health.get("wordnik", {})
    invalid_validation = value_from_sources(
        words_by_source.get("invalid_list_validation"),
        len(promoted_words) if promoted_words is not None else None,
    )

    return f"""
## Execution Transparency

**API Health Check**
- Merriam-Webster API calls: {display_count(mw_health.get('calls_made'))} ({display_count(mw_health.get('success_rate'))} success rate)
- Wordnik API calls: {display_count(wordnik_health.get('calls_made'))} ({display_count(wordnik_health.get('success_rate'))} success rate)

**Words Discovered by Source**
- Merriam-Webster RSS / New Words: {display_count(sum_recorded_values(words_by_source.get('merriam_webster_rss'), words_by_source.get('merriam_webster_new_words')))}
- Wordnik Word of the Day: {display_count(words_by_source.get('wordnik_wotd'))}
- Invalid list validation: {display_count(invalid_validation)}
- Manual additions: {display_count(words_by_source.get('manual_additions'))}

Missing historical metrics are shown as `{NOT_RECORDED}` rather than reconstructed.
"""


def render_release_files(release_dir: Path) -> str:
    """Render release file links only for files expected in the release folder."""
    descriptions = {
        "starting_letter_distribution.csv": "starting-letter distribution used for charts when available",
        "word_length_distribution.csv": "word-length distribution used for charts when available",
        "CHANGELOG.md": "detailed process log",
        "update_stats.json": "machine-readable update summary",
        "daily_execution_summary.json": "machine-readable execution transparency summary",
    }
    lines = [
        f"- `{name}` — {description}"
        for name, description in descriptions.items()
        if (release_dir / name).exists()
    ]
    if not lines:
        lines = [f"- Release file details were {UNAVAILABLE} for this generated post."]
    return "\n".join(lines)


def generate_blog_post(
    release_date: str | None = None,
    generated_at: datetime | None = None,
    posts_dir: Path = BLOG_POSTS_DIR,
    release_dir: Path | None = None,
) -> Path:
    """Generate one daily blog post."""
    release_date = release_date or get_release_date()
    release_dir = release_dir or OUTPUT_DIR / release_date
    posts_dir.mkdir(parents=True, exist_ok=True)

    overall_stats = load_json(OVERALL_STATS_FILE, {})
    update_stats = load_json(release_dir / "update_stats.json", {})
    execution_summary = load_json(release_dir / "daily_execution_summary.json", {})

    promoted_words = list_from_stats(update_stats, "promoted_words")
    if promoted_words is None:
        promoted_words = load_promoted_words(release_dir)
    new_words = list_from_stats(update_stats, "new_words")
    chart_data = build_chart_data(release_dir)

    promoted_count = len(promoted_words) if promoted_words is not None else None
    new_words_count = len(new_words) if new_words is not None else None
    words_added_today = (
        promoted_count + new_words_count
        if promoted_count is not None and new_words_count is not None
        else None
    )

    total_valid_words = value_from_sources(
        update_stats.get("total_valid_after"),
        overall_stats.get("total_valid_words") if overall_stats.get("last_updated") == release_date else None,
    )
    total_invalid_entries = value_from_sources(
        update_stats.get("total_invalid_after"),
        overall_stats.get("total_invalid_entries") if overall_stats.get("last_updated") == release_date else None,
    )

    generated_at = generated_at or datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    timestamp = generated_at.strftime("%Y-%m-%d %H:%M:%S")
    full_timestamp = generated_at.isoformat()

    post_content = f"""---
layout: post
title: "Daily English OpenList Update - {release_date}"
date: {full_timestamp}
categories: [daily-updates]
tags: [daily, statistics, words]
excerpt: "Automated English OpenList daily update for {release_date}."
---

# Daily English OpenList Update — {release_date}

**Generated automatically at {timestamp} UTC**

This automated post follows the English OpenList Blog Constitution by reporting only recorded values. Missing historical metrics are marked as `{NOT_RECORDED}` or `{UNAVAILABLE}`.

## Today's Results

- **Total words added today:** {display_count(words_added_today)}
- **New words discovered today:** {display_count(new_words_count)}
- **Words promoted from invalid list:** {display_count(promoted_count)}
- **Total valid words now:** **{display_count(total_valid_words)}**
- **Total invalid entries tracked:** {display_count(total_invalid_entries)}
{render_words_section('New Words Discovered Today', new_words)}{render_words_section('Words Promoted Today', promoted_words)}{render_charts_section(chart_data)}{render_execution_summary(execution_summary, promoted_words)}
## Release Files

{render_release_files(release_dir)}

*Generated automatically by the English OpenList daily pipeline.*
"""

    post_path = posts_dir / f"{release_date}-daily-update.md"
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(post_content)

    logger.info("Blog post created: %s", post_path)
    return post_path


def main():
    print("Generating daily blog post...")
    post_path = generate_blog_post()
    print(f"Done: {post_path}")
    return 0


if __name__ == "__main__":
    exit(main())
