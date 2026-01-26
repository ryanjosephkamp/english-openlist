"""
Consolidated Changelog Generator
Generates a unified changelog after both new word discovery and invalid list validation.

This script:
1. Reads update_stats.json from new word discovery
2. Reads promoted_words.txt from invalid list validation
3. Generates a consolidated CHANGELOG.md with all information
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR, get_release_date, get_release_dir

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_update_stats(release_dir: Path) -> dict:
    """Load update stats from new word discovery."""
    stats_file = release_dir / "update_stats.json"
    if stats_file.exists():
        with open(stats_file, 'r') as f:
            return json.load(f)
    return {
        "words_added_to_valid": 0,
        "words_removed_from_invalid": 0,
        "total_valid_after": 0,
        "total_invalid_after": 0,
        "new_words": [],
        "promoted_words": [],
        "timestamp": datetime.now().isoformat(),
    }


def load_promoted_words(release_dir: Path) -> list[str]:
    """Load promoted words from invalid list validation."""
    promoted_file = release_dir / "promoted_words.txt"
    if promoted_file.exists():
        with open(promoted_file, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return []


def load_validation_progress(phase3_root: Path) -> dict:
    """Load validation progress to get today's stats."""
    progress_file = phase3_root / "validation_progress.json"
    if progress_file.exists():
        with open(progress_file, 'r') as f:
            return json.load(f)
    return {
        "validated_count": 0,
        "promoted_count": 0,
    }


def load_rss_discovered_count(release_dir: Path) -> int:
    """Load count of words discovered from RSS feed."""
    stats_file = release_dir / "update_stats.json"
    if stats_file.exists():
        with open(stats_file, 'r') as f:
            stats = json.load(f)
            # The 'new_words' field contains validated new words from RSS/manual
            return len(stats.get("new_words", []))
    return 0


def generate_changelog(release_date: str = None) -> None:
    """
    Generate consolidated changelog for the given release date.
    
    Args:
        release_date: Date string in YYYY-MM-DD format (default: today)
    """
    release_date = release_date or get_release_date()
    release_dir = OUTPUT_DIR / release_date
    release_dir.mkdir(parents=True, exist_ok=True)
    
    phase3_root = Path(__file__).parent.parent
    
    # Load data from both pipeline stages
    update_stats = load_update_stats(release_dir)
    promoted_from_invalid = load_promoted_words(release_dir)
    validation_progress = load_validation_progress(phase3_root)
    
    # Calculate totals
    new_words = update_stats.get("new_words", [])
    words_added_from_discovery = len(new_words)
    words_promoted_from_invalid = len(promoted_from_invalid)
    total_words_added = words_added_from_discovery + words_promoted_from_invalid
    
    # Get totals (from update stats, but add promoted words to valid count)
    total_valid = update_stats.get("total_valid_after", 0) + words_promoted_from_invalid
    total_invalid = update_stats.get("total_invalid_after", 0) - words_promoted_from_invalid
    if total_invalid < 0:
        total_invalid = 0  # Safety check
    
    # Get validation stats for today
    words_validated_today = validation_progress.get("validated_count", 0)
    
    # Generate changelog content
    changelog_file = release_dir / "CHANGELOG.md"
    
    content = f"""# English OpenList Changelog

## [{release_date}] - Daily Update

### Summary
- **New Words Added (from Discovery):** {words_added_from_discovery}
- **Words Promoted (Invalid → Valid):** {words_promoted_from_invalid}
- **Total Words Added Today:** {total_words_added}
- **Total Valid Words:** {total_valid:,}
- **Total Invalid Words:** {total_invalid:,}

### New Words from Automated Discovery
_Sources: Merriam-Webster RSS, MW New Words Page, Wordnik Word of the Day_

"""
    
    if new_words:
        content += "| Word | Source |\n|------|--------|\n"
        for word in new_words:
            content += f"| {word} | Dictionary API |\n"
    else:
        content += "_No new words discovered today._\n"
    
    content += "\n### Words Promoted from Invalid to Valid\n"
    
    if promoted_from_invalid:
        content += f"\n_Validated {validation_progress.get('validated_count', 0):,} words from the invalid list today._\n\n"
        content += "| Word | Status |\n|------|--------|\n"
        for word in promoted_from_invalid:
            content += f"| {word} | Promoted ✓ |\n"
    else:
        if words_validated_today > 0:
            content += f"_Validated {words_validated_today:,} words from invalid list. No words promoted today._\n"
        else:
            content += "_No invalid list validation performed today._\n"
    
    content += f"""
### Technical Notes
- Update completed at: {datetime.now().isoformat()}
- Words discovered from automated sources: {len(update_stats.get('new_words', []))}
- Words validated from invalid list: {validation_progress.get('validated_count', 0)}
- Cumulative words validated from invalid list: {validation_progress.get('validated_count', 0):,}
- Cumulative promotions from invalid list: {validation_progress.get('promoted_count', 0):,}

### Discovery Sources
- **Merriam-Webster RSS**: Word of the Day feed
- **Merriam-Webster New Words**: Newly added dictionary entries
- **Wordnik Word of the Day**: Past 30 days of featured words
"""
    
    with open(changelog_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"Generated consolidated changelog: {changelog_file}")
    logger.info(f"  New words from discovery: {words_added_from_discovery}")
    logger.info(f"  Words promoted from invalid: {words_promoted_from_invalid}")
    logger.info(f"  Total words added: {total_words_added}")
    
    # Also update the update_stats.json to include promoted words
    update_stats["promoted_words"] = promoted_from_invalid
    update_stats["words_removed_from_invalid"] = words_promoted_from_invalid
    update_stats["total_valid_after"] = total_valid
    update_stats["total_invalid_after"] = total_invalid
    
    stats_file = release_dir / "update_stats.json"
    with open(stats_file, 'w') as f:
        json.dump(update_stats, f, indent=2)
    logger.info(f"Updated stats file: {stats_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate consolidated changelog")
    parser.add_argument("--date", type=str, default=None,
                        help="Release date (YYYY-MM-DD format, default: today)")
    args = parser.parse_args()
    
    generate_changelog(args.date)
    
    print("Changelog generated successfully!")


if __name__ == "__main__":
    main()
