"""
Daily Blog Post Generator (Robust Debug Version)
Always creates a blog post, even with limited data.
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


def load_json_safe(path: Path) -> dict:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load {path}: {e}")
    return {}


def get_next_update_number() -> int:
    try:
        if UPDATES_LOG_FILE.exists():
            with open(UPDATES_LOG_FILE, "r", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))
                if reader:
                    return int(reader[-1].get("update_number", 0)) + 1
    except Exception:
        pass
    return 1  # Default to 1 if anything fails


def load_daily_data_safe(release_dir: Path) -> dict:
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
        "promoted_words": "(No promoted words data available in this run)"
    }

    # Try to load promoted words
    promoted_file = release_dir / "promoted_words.txt"
    if promoted_file.exists():
        try:
            with open(promoted_file, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                data["promoted_count"] = len(lines)
                data["promoted_words"] = "\n".join(lines[:30])
        except Exception as e:
            logger.warning(f"Error reading promoted_words: {e}")

    # Try to load update stats
    stats_file = release_dir / "update_stats.json"
    if stats_file.exists():
        stats = load_json_safe(stats_file)
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
    overall = load_json_safe(OVERALL_STATS_FILE)

    update_number = get_next_update_number()
    daily_data = load_daily_data_safe(release_dir)

    # Prepare chart data
    length_dist = overall.get("word_length_distribution", {})
    letter_dist = overall.get("starting_letter_distribution", {})

    length_labels = json.dumps(list(length_dist.keys())) if length_dist else "[]"
    length_values = json.dumps(list(length_dist.values())) if length_dist else "[]"
    letter_labels = json.dumps(list(letter_dist.keys())) if letter_dist else "[]"
    letter_values = json.dumps(list(letter_dist.values())) if letter_dist else "[]"

    # Load template
    template_path = TEMPLATES_DIR / "daily_blog_post.md"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()
    except Exception:
        template = "# Daily Update Placeholder\n\nBlog post generation had an issue loading the template."

    # Fill placeholders
    post_content = template
    post_content = post_content.replace("{{ update_number }}", str(update_number))
    post_content = post_content.replace("{{ date }}", release_date)
    post_content = post_content.replace("{{ full_timestamp }}", datetime.now(timezone.utc).isoformat() + "Z")
    post_content = post_content.replace("{{ timestamp }}", daily_data["timestamp"])
    post_content = post_content.replace("{{ promoted_count }}", str(daily_data["promoted_count"]))
    post_content = post_content.replace("{{ new_words_total }}", str(daily_data["new_words_total"]))
    post_content = post_content.replace("{{ total_valid_words }}", str(overall.get("total_valid_words", "N/A")))
    post_content = post_content.replace("{{ total_invalid_entries }}", str(overall.get("total_invalid_entries", "N/A")))
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

    # Write the post
    BLOG_POSTS_DIR.mkdir(parents=True, exist_ok=True)
    post_filename = f"{release_date}-daily-update-{update_number}.md"
    post_path = BLOG_POSTS_DIR / post_filename

    with open(post_path, "w", encoding="utf-8") as f:
        f.write(post_content)

    if post_path.exists():
        logger.info(f"SUCCESS: Blog post written ({post_path.stat().st_size} bytes)")
    else:
        logger.error("FAILED to write blog post")
        raise FileNotFoundError(str(post_path))

    return post_path


def main():
    print("=" * 60)
    print("English OpenList - Daily Blog Post Generator (Robust)")
    print("=" * 60)

    try:
        post_path = generate_blog_post()
        print(f"Blog post created: {post_path}")
    except Exception as e:
        logger.error(f"Generator failed: {e}")
        # Create a fallback post so the workflow doesn't completely fail
        fallback_path = BLOG_POSTS_DIR / f"{get_release_date()}-daily-update-fallback.md"
        with open(fallback_path, "w", encoding="utf-8") as f:
            f.write(f"# Daily Update - {get_release_date()}\n\nGenerator encountered an error. Check logs.")
        print(f"Fallback post created: {fallback_path}")

    print("Done.")
    return 0


if __name__ == "__main__":
    exit(main())
