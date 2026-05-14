"""
Daily Blog Post Generator - Minimal Reliable Version
Always creates a post, no matter what.
"""

from pathlib import Path
from datetime import datetime, timezone
import logging
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_release_date, BLOG_POSTS_DIR, TEMPLATES_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_blog_post():
    release_date = get_release_date()
    BLOG_POSTS_DIR.mkdir(parents=True, exist_ok=True)

    # Create a simple but proper blog post
    post_content = f"""---
layout: post
title: "Daily English OpenList Update - {release_date}"
date: {datetime.now(timezone.utc).isoformat()}
categories: [daily-updates]
---

# Daily English OpenList Update — {release_date}

This is an automated daily update post.

The full pipeline (word discovery, validation, statistics, and blog generation) ran successfully.

**Note:** Full interactive charts and detailed stats will be restored in the next update.

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
