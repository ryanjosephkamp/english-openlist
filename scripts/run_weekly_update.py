"""
Weekly Update Pipeline - Main Orchestration Script
English OpenList Phase 3

This script orchestrates the complete weekly update process:
1. Discover new words from dictionary sources
2. Validate new words against rules
3. Update valid/invalid word lists
4. Generate statistics and visualizations
5. Create changelog
6. Package release files
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    PHASE3_ROOT, OUTPUT_DIR, LOG_FILE, LOG_LEVEL, LOG_FORMAT,
    VALID_WORDS_FILE, VALID_DICT_FILE,
    get_release_date, get_release_dir
)
from scripts.dictionary_api import DictionaryAPIClient, WordStatus
from scripts.word_validator import WordValidator
from scripts.data_updater import DataUpdater, DataManager, create_word_metadata

# Ensure logs directory exists
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode='a')
    ]
)
logger = logging.getLogger(__name__)


class NewWordDiscoverer:
    """
    Discovers new words from various sources.
    
    Sources:
    1. Merriam-Webster RSS feed for "Word of the Day"
    2. Wordnik Word of the Day (past N days)
    3. Manual word list (for testing/additions) - kept as fallback

    Merriam-Webster's "New Words" web page is not a source. It is a page for
    people, not an API: it answers this run with 403, and scraping it may break
    the site's terms.
    """
    
    def __init__(self):
        self.discovered_words: list[str] = []
    
    async def discover_from_rss(self) -> list[str]:
        """
        Parse Merriam-Webster RSS feed for words.
        
        Note: This discovers the Word of the Day, not necessarily new words.
        The RSS feed format uses the word directly as the title (e.g., "oaf")
        rather than "Word of the Day: oaf".
        """
        try:
            import feedparser
            from config import NEW_WORD_SOURCES
            
            feed_url = NEW_WORD_SOURCES.get("merriam_webster_rss")
            if not feed_url:
                return []
            
            # feedparser is synchronous, run in executor
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, feed_url)
            
            words = []
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                
                # Handle both formats:
                # 1. Old format: "Word of the Day: {word}"
                # 2. Current format: just the word (e.g., "oaf")
                if ":" in title:
                    word = title.split(":")[-1].strip().lower()
                elif title:
                    # Title is just the word itself
                    word = title.lower()
                else:
                    continue
                
                # Basic validation: only alphabetic words
                if word and word.isalpha():
                    words.append(word)
            
            logger.info(f"Discovered {len(words)} words from MW RSS feed")
            return words
            
        except ImportError:
            logger.warning("feedparser not installed, skipping RSS discovery")
            return []
        except Exception as e:
            logger.error(f"Error parsing RSS feed: {e}")
            return []
    
    async def discover_from_wordnik(self) -> list[str]:
        """
        Discover words from Wordnik's Word of the Day.
        
        Fetches the past N days of Word of the Day to find interesting words.
        Note: Wordnik Basic plan has API rate limits (100 calls/day).
        
        Returns:
            List of words from Wordnik Word of the Day
        """
        try:
            import httpx
            from datetime import timedelta
            from config import WORDNIK_API_KEY, NEW_WORD_SOURCES, WORDNIK_WOTD_LOOKBACK_DAYS
            
            if not WORDNIK_API_KEY:
                logger.debug("No Wordnik API key configured, skipping Wordnik discovery")
                return []
            
            base_url = NEW_WORD_SOURCES.get("wordnik_wotd")
            if not base_url:
                return []
            
            words = []
            
            async with httpx.AsyncClient(timeout=15) as client:
                # Fetch Word of the Day for the past N days
                # Use fewer days to stay within rate limits
                days_to_fetch = min(WORDNIK_WOTD_LOOKBACK_DAYS, 30)
                
                for days_ago in range(days_to_fetch):
                    date = datetime.now() - timedelta(days=days_ago)
                    date_str = date.strftime("%Y-%m-%d")
                    
                    try:
                        response = await client.get(
                            base_url,
                            params={"api_key": WORDNIK_API_KEY, "date": date_str}
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            word = data.get('word', '')
                            if word and word.isalpha():
                                words.append(word.lower())
                        elif response.status_code == 429:
                            # Rate limited - stop fetching
                            logger.warning("Wordnik API rate limit reached, stopping fetch")
                            break
                        
                        # Small delay to be respectful of API
                        await asyncio.sleep(0.2)
                        
                    except Exception as e:
                        logger.debug(f"Error fetching Wordnik WOTD for {date_str}: {e}")
                        continue
            
            # Deduplicate
            unique_words = list(set(words))
            logger.info(f"Discovered {len(unique_words)} words from Wordnik WOTD")
            return unique_words
            
        except ImportError:
            logger.warning("httpx not installed, skipping Wordnik discovery")
            return []
        except Exception as e:
            logger.error(f"Error fetching from Wordnik: {e}")
            return []
    
    async def discover_from_manual_list(self, filepath: Path) -> list[str]:
        """
        Read words from a manual additions file.
        
        Args:
            filepath: Path to file with one word per line (lines starting with # are comments)
            
        Returns:
            List of words from the file
        """
        if not filepath.exists():
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                words = []
                for line in f:
                    line = line.strip().lower()
                    # Skip empty lines and comments
                    if line and not line.startswith('#') and line.isalpha():
                        words.append(line)
            if words:
                logger.info(f"Loaded {len(words)} words from manual list")
            return words
        except Exception as e:
            logger.error(f"Error reading manual word list: {e}")
            return []
    
    async def discover_all(self) -> list[str]:
        """
        Run all discovery methods and combine results.
        
        Returns:
            Deduplicated list of discovered words
        """
        all_words = set()
        
        # 1. Merriam-Webster RSS feed (Word of the Day)
        rss_words = await self.discover_from_rss()
        all_words.update(rss_words)
        
        # 2. Wordnik Word of the Day
        wordnik_words = await self.discover_from_wordnik()
        all_words.update(wordnik_words)
        
        # 3. Manual additions file (fallback/testing)
        manual_file = PHASE3_ROOT / "manual_additions.txt"
        manual_words = await self.discover_from_manual_list(manual_file)
        all_words.update(manual_words)
        
        self.discovered_words = list(all_words)
        logger.info(f"Total discovered words: {len(self.discovered_words)}")
        
        return self.discovered_words


class WeeklyUpdatePipeline:
    """
    Main pipeline for weekly dictionary updates.
    """
    
    def __init__(self, skip_invalid: bool = False):
        self.discoverer = NewWordDiscoverer()
        self.validator = WordValidator()
        self.api_client = DictionaryAPIClient()
        self.data_manager = DataManager(skip_invalid=skip_invalid)
        self.updater = DataUpdater(self.data_manager)
        
        self.release_date = get_release_date()
        self.release_dir = get_release_dir()
        
        # Results
        self.discovered_words: list[str] = []
        self.validated_words: list[dict] = []
        self.not_checked: list[str] = []
        self.update_stats = None
    
    async def run(self) -> dict:
        """
        Run the complete weekly update pipeline.
        
        Returns:
            Dictionary with pipeline results
        """
        start_time = datetime.now()
        logger.info(f"Starting weekly update pipeline for {self.release_date}")
        
        try:
            # The update rewrites these files. Find out now if that cannot work,
            # before any dictionary lookup is spent.
            read_only = [
                str(path) for path in (VALID_WORDS_FILE, VALID_DICT_FILE)
                if path.exists() and not os.access(path, os.W_OK)
            ]
            if read_only:
                raise PermissionError(f"Cannot write the source files: {', '.join(read_only)}")

            # Step 1: Load existing data
            logger.info("Step 1: Loading existing data...")
            self.data_manager.load_data()
            existing_valid = self.data_manager.valid_words
            existing_invalid = self.data_manager.invalid_words
            logger.info(f"  Current valid words: {len(existing_valid)}")
            logger.info(f"  Current invalid words: {len(existing_invalid)}")
            
            # Step 2: Discover new word candidates
            logger.info("Step 2: Discovering new word candidates...")
            self.discovered_words = await self.discoverer.discover_all()
            
            # Filter out words already in valid list
            new_candidates = [
                w for w in self.discovered_words
                if w not in existing_valid
            ]
            logger.info(f"  New candidates to check: {len(new_candidates)}")
            
            # Step 3: Validate candidates against rules
            logger.info("Step 3: Validating candidates against rules...")
            rule_valid, rule_invalid = self.validator.validate_batch(new_candidates)
            logger.info(f"  Passed rule validation: {len(rule_valid)}")
            logger.info(f"  Failed rule validation: {len(rule_invalid)}")
            
            # Step 4: Validate against dictionary API
            logger.info("Step 4: Checking dictionary API...")
            for word in rule_valid:
                result = await self.api_client.lookup_word(word)
                
                if not result.checked:
                    # A 403, a 429, or another error: not a verdict. The word
                    # is not added, and nothing records it as rejected.
                    self.not_checked.append(word)
                elif result.status == WordStatus.VALID:
                    self.validated_words.append({
                        "word": word,
                        "metadata": create_word_metadata(
                            word=word,
                            source=result.source,
                            part_of_speech=result.part_of_speech,
                            definition=result.definition,
                            pronunciation=result.pronunciation,
                            etymology=result.etymology
                        )
                    })
                    logger.debug(f"  ✓ {word} - valid")
                elif result.status == WordStatus.PROPER_NOUN:
                    logger.debug(f"  ✗ {word} - proper noun")
                elif result.status == WordStatus.ABBREVIATION:
                    logger.debug(f"  ✗ {word} - abbreviation/acronym")
                elif result.status == WordStatus.NOT_FOUND:
                    logger.debug(f"  ✗ {word} - not in dictionary")
                else:
                    logger.debug(f"  ? {word} - {result.status.value}")
            
            logger.info(f"  API validated: {len(self.validated_words)}")
            logger.info(f"  Not checked tonight: {len(self.not_checked)}")
            if self.api_client.refused:
                logger.info(f"  Sources that refused tonight: {self.api_client.refused}")
            
            # Step 5: Update data
            logger.info("Step 5: Updating word lists...")
            self.update_stats = self.updater.run_update(
                self.validated_words,
                self.release_dir
            )
            
            # Step 6: Generate statistics (placeholder - will be in separate module)
            logger.info("Step 6: Generating statistics...")
            self._save_update_stats()
            
            # Step 7: Generate changelog (placeholder - will be in separate module)
            logger.info("Step 7: Generating changelog...")
            self._generate_changelog()
            
            # Complete
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Pipeline complete in {duration:.1f} seconds")
            logger.info(f"  Words added: {self.update_stats.words_added_to_valid}")
            logger.info(f"  Words promoted: {self.update_stats.words_removed_from_invalid}")
            
            return {
                "success": True,
                "release_date": self.release_date,
                "duration_seconds": duration,
                "words_discovered": len(self.discovered_words),
                "words_validated": len(self.validated_words),
                "words_added": self.update_stats.words_added_to_valid,
                "words_promoted": self.update_stats.words_removed_from_invalid,
                "total_valid": self.update_stats.total_valid_after,
                "total_invalid": self.update_stats.total_invalid_after,
            }
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "release_date": self.release_date,
            }
    
    def _save_update_stats(self) -> None:
        """Save update statistics to JSON file."""
        import json
        
        stats_file = self.release_dir / "update_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.update_stats.to_dict(), f, indent=2)
        logger.info(f"Saved statistics to {stats_file}")
    
    def _generate_changelog(self) -> None:
        """Generate changelog markdown file."""
        changelog_file = self.release_dir / "CHANGELOG.md"
        
        content = f"""# English OpenList Changelog

## [{self.release_date}] - Weekly Update

### Summary
- **Words Added:** {self.update_stats.words_added_to_valid}
- **Words Promoted (Invalid → Valid):** {self.update_stats.words_removed_from_invalid}
- **Total Valid Words:** {self.update_stats.total_valid_after:,}
- **Total Invalid Words:** {self.update_stats.total_invalid_after:,}

### New Words Added
"""
        
        if self.update_stats.new_words:
            content += "| Word | Source |\n|------|--------|\n"
            for word in self.update_stats.new_words:
                content += f"| {word} | Dictionary API |\n"
        else:
            content += "_No new words added this week._\n"
        
        content += "\n### Words Promoted from Invalid to Valid\n"
        
        if self.update_stats.promoted_words:
            for word in self.update_stats.promoted_words:
                content += f"- {word}\n"
        else:
            content += "_No words promoted this week._\n"
        
        content += f"""
### Technical Notes
- Update completed at: {self.update_stats.timestamp}
- Words discovered: {len(self.discovered_words)}
- Words validated via API: {len(self.validated_words)}
"""
        
        with open(changelog_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Saved changelog to {changelog_file}")


async def main():
    """Main entry point for the weekly update pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="English OpenList Weekly Update Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Run without saving changes")
    parser.add_argument("--limit", type=int, help="Limit number of words to check (for testing)")
    parser.add_argument("--skip-invalid", action="store_true", help="Skip loading invalid words (saves memory)")
    args = parser.parse_args()
    
    print("=" * 60)
    print("English OpenList - Weekly Update Pipeline")
    print("=" * 60)
    
    pipeline = WeeklyUpdatePipeline(skip_invalid=args.skip_invalid)
    results = await pipeline.run()
    
    print("\n" + "=" * 60)
    if results["success"]:
        print("UPDATE SUCCESSFUL")
        print(f"  Release Date: {results['release_date']}")
        print(f"  Duration: {results['duration_seconds']:.1f} seconds")
        print(f"  Words Added: {results['words_added']}")
        print(f"  Words Promoted: {results['words_promoted']}")
        print(f"  Total Valid: {results['total_valid']:,}")
    else:
        print("UPDATE FAILED")
        print(f"  Error: {results.get('error', 'Unknown error')}")
    print("=" * 60)
    
    return results


def exit_code(results: dict) -> int:
    """0 when the update ran, 1 when it failed, so the step fails with it."""
    return 0 if results.get("success") else 1


if __name__ == "__main__":
    sys.exit(exit_code(asyncio.run(main())))
