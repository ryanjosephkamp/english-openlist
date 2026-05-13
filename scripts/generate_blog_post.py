"""
Daily Blog Post Generator
Reads data from the daily release folder and overall_stats.json,
then generates a beautiful Jekyll blog post.

Output: _posts/YYYY-MM-DD-daily-update-N.md
"""

import json
import csv
from pathlib import Path
from datetime import datetime, timezone
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    get_release_dir,
    get_release_date,
    OVERALL_STATS_FILE,
    UPDATES_LOG_FILE,
    BLOG_POSTS_DIR,
    TEMPLATES_DIR
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_csv_last_row(path: Path) -> dict:
    """Read the last row of the updates log to get the latest update number."""
    if not path.exists():
        return {"update_number": 0}
    with open(path, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
        if reader:
            return reader[-1]
    return {"update_number": 0}


def get_next_update_number() -> int:
    last = load_csv_last_row(UPDATES_LOG_FILE)
    try:
        return int(last.get("update_number", 0)) + 1
    except:
        return 1


def load_daily_data(release_dir: Path) -> dict:
    """Load all data needed for the blog post from the daily release folder."""
    data = {
        "date": get_release_date(),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "promoted_count": 0,
        "new_words_total": 0,
        "from_rss": 0,
        "from_wordnik": 0,
        "from_invalid": 0,
        "from_manual": 0,
        "api_calls_mw": 0,
        "api_calls_wordnik": 0,
        "promoted_words": ""
    }

    promoted_file = release_dir / "promoted_words.txt"
    if promoted_file.exists():
        with open(promoted_file, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
            data["promoted_count"] = len(lines)
            data["promoted_words"] = "\n".join(lines[:20])

    stats_file = release_dir / "update_stats.json"
    if stats_file.exists():
        stats = load_json(stats_file)
        data.update({
            "new_words_total": stats.get("new_words_total", 0),
            "from_rss": stats.get("from_rss", 0),
            "from_wordnik": stats.get("from_wordnik", 0),
            "from_invalid": stats.get("from_invalid", 0),
            "from_manual": stats.get("from_manual", 0),
            "api_calls_mw": stats.get("api_calls_mw", 0),
            "api_calls_wordnik": stats.get("api_calls_wordnik", 0),
        })

    return data


def generate_blog_post():
    release_date = get_release_date()
    release_dir = get_release_dir()
    overall = load_json(OVERALL_STATS_FILE)

    update_number = get_next_update_number()
    daily_data = load_daily_data(release_dir)

    length_dist = overall.get("word_length_distribution", {})
    letter_dist = overall.get("starting_letter_distribution", {})

    length_labels = json.dumps(list(length_dist.keys()))
    length_values = json.dumps(list(length_dist.values()))
    letter_labels = json.dumps(list(letter_dist.keys()))
    letter_values = json.dumps(list(letter_dist.values()))

    template_path = TEMPLATES_DIR / "daily_blog_post.md"
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    post_content = template
    post_content = post_content.replace("{{ update_number }}", str(update_number))
    post_content = post_content.replace("{{ date }}", release_date)
    post_content = post_content.replace("{{ full_timestamp }}", datetime.now(timezone.utc).isoformat() + "Z")
    post_content = post_content.replace("{{ timestamp }}", daily_data["timestamp"])
    post_content = post_content.replace("{{ promoted_count }}", str(daily_data["promoted_count"]))
    post_content = post_content.replace("{{ new_words_total }}", str(daily_data["new_words_total"]))
    post_content = post_content.replace("{{ total_valid_words }}", str(overall.get("total_valid_words", 0)))
    post_content = post_content.replace("{{ total_invalid_entries }}", str(overall.get("total_invalid_entries", 0)))
    post_content = post_content.replace("{{ length_labels | safe }}", length_labels)
    post_content = post_content.replace("{{ length_values | safe }}", length_values)
    post_content = post_content.replace("{{ letter_labels | safe }}", letter_labels)
    post_content = post_content.replace("{{ letter_values | safe }}", letter_values)
    post_content = post_content.replace("{{ api_calls_mw }}", str(daily_data["api_calls_mw"]))
    post_content = post_content.replace("{{ api_calls_wordnik }}", str(daily_data["api_calls_wordnik"]))
    post_content = post_content.replace("{{ from_rss }}", str(daily_data["from_rss"]))
    post_content = post_content.replace("{{ from_wordnik }}", str(daily_data["from_wordnik"]))
    post_content = post_content.replace("{{ from_invalid }}", str(daily_data["from_invalid"]))
    post_content = post_content.replace("{{ from_manual }}", str(daily_data["from_manual"]))
    post_content = post_content.replace("{{ promoted_words }}", daily_data["promoted_words"])
    post_content = post_content.replace("{{ prev_number }}", str(update_number - 1) if update_number > 1 else "N/A")
    post_content = post_content.replace("{{ prev_url }}", "#")

    BLOG_POSTS_DIR.mkdir(parents=True, exist_ok=True)
    post_filename = f"{release_date}-daily-update-{update_number}.md"
    post_path = BLOG_POSTS_DIR / post_filename

    with open(post_path, "w", encoding="utf-8") as f:
        f.write(post_content)

    if post_path.exists():
        logger.info(f"SUCCESS: Blog post written to {post_path} (size: {post_path.stat().st_size} bytes)")
    else:
        logger.error(f"FAILED to write blog post to {post_path}")
        raise FileNotFoundError(f"Blog post was not created: {post_path}")

    return post_path


def main():
    print("=" * 60)
    print("English OpenList - Daily Blog Post Generator")
    print("=" * 60)

    post_path = generate_blog_post()
    print(f"\nBlog post created: {post_path}")
    print("Phase 3 complete!")
    return 0


if __name__ == "__main__":
    exit(main())
