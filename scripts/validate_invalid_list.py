"""
Invalid List Validator
Systematically validates words from the invalid list against dictionary APIs.

This script:
1. Loads the invalid word list
2. Scores words by likelihood of being valid (prioritization)
3. Queries dictionary APIs for top candidates
4. Promotes validated words to the valid list
5. Tracks progress for resumption

Run daily to recover ~50-100 false negatives per day.
"""

import asyncio
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import random

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    INVALID_WORDS_FILE, VALID_WORDS_FILE, VALID_DICT_FILE,
    DAILY_VALIDATION_LIMIT, VALIDATION_BATCH_SIZE,
    OUTPUT_DIR, PHASE3_ROOT, get_release_date
)
from scripts.dictionary_api import DictionaryAPIClient, WordStatus
from scripts.word_validator import WordValidator

logger = logging.getLogger(__name__)


@dataclass
class CandidateWord:
    """A word candidate with its priority score."""
    word: str
    score: float
    reasons: list = field(default_factory=list)


class WordPrioritizer:
    """
    Scores words by likelihood of being valid English words.
    
    Higher scores = more likely to be valid (should check first).
    
    Strategy: Apply strict pre-filtering to eliminate obviously non-English words,
    then score remaining candidates.
    """
    
    # Productive prefixes that generate many invalid compounds
    PRODUCTIVE_PREFIXES = {
        'anti', 'non', 'pre', 'post', 'multi', 'semi', 'pseudo', 'quasi',
        'ultra', 'super', 'hyper', 'mega', 'micro', 'macro', 'neo', 'proto',
        'counter', 'inter', 'intra', 'extra', 'trans'
    }
    
    # Good prefixes that appear in real words
    REAL_WORD_PREFIXES = {'un', 're', 'dis', 'mis', 'over', 'out', 'under'}
    
    # Common English suffixes
    SUFFIXES = {
        'ing', 'ed', 'er', 'est', 'ly', 'tion', 'sion', 'ness', 'ment',
        'able', 'ible', 'ful', 'less', 'ous', 'ive', 'al', 'ical',
        'ity', 'ance', 'ence', 'ism', 'ist'
    }
    
    # Patterns that indicate non-English words (foreign, OCR errors, etc.)
    NON_ENGLISH_PATTERNS = [
        r'(.)\1{2,}',  # Triple+ repeated letters
        r'^[^aeiou]{5,}',  # 5+ consonants at start
        r'[^aeiou]{5,}',  # 5+ consecutive consonants anywhere
        r'[aeiou]{4,}',  # 4+ consecutive vowels
        r'q(?!u)',  # q not followed by u
        r'[jkqvwxz]{3,}',  # 3+ rare consonants in a row
        r'[^a-z]',  # Non-letter characters
        # Foreign language patterns
        r'szcz|zcz|tsz|cz[aeiou]',  # Polish
        r'ough$|ght$',  # Already valid common patterns - skip
        r'schw|tsch',  # German
        r'ção|ões|ão$',  # Portuguese
        r'ñ|ü|ö|ä|ß',  # Diacritics
        r'^[^aeiou]{4}',  # 4 consonants at start
        r'[^aeiou]{4}$',  # 4 consonants at end
        r'kh|gh[^t]|zh|dj',  # Transliteration patterns
    ]
    
    def __init__(self):
        self.non_english = [re.compile(p) for p in self.NON_ENGLISH_PATTERNS]
    
    def is_likely_english(self, word: str) -> bool:
        """
        Quick pre-filter to eliminate obviously non-English words.
        Returns True if word might be English.
        """
        # Length check - very short or very long words unlikely
        if len(word) < 3 or len(word) > 15:
            return False
        
        # Check for non-English patterns
        for pattern in self.non_english:
            if pattern.search(word):
                return False
        
        # Check vowel ratio - English words have 20-50% vowels
        vowels = sum(1 for c in word if c in 'aeiou')
        ratio = vowels / len(word)
        if ratio < 0.15 or ratio > 0.6:
            return False
        
        # Skip productive prefix compounds
        for prefix in self.PRODUCTIVE_PREFIXES:
            if word.startswith(prefix) and len(word) > len(prefix) + 3:
                return False
        
        return True
    
    def score_word(self, word: str) -> CandidateWord:
        """
        Score a word's likelihood of being valid.
        
        Returns:
            CandidateWord with score (0-100) and reasons
        """
        score = 50.0  # Start at neutral
        reasons = []
        length = len(word)
        if 3 <= length <= 5:
            score += 25
            reasons.append(f"short word ({length} chars)")
        elif 6 <= length <= 8:
            score += 15
            reasons.append(f"medium word ({length} chars)")
        elif 9 <= length <= 12:
            score += 5
            reasons.append(f"longer word ({length} chars)")
        elif length == 2:
            score += 10
            reasons.append("2-letter word")
        elif 13 <= length <= 16:
            score -= 10
            reasons.append("long word")
        else:
            score -= 30
            reasons.append(f"very long ({length} chars)")
        
        # PENALIZE productive prefix compounds heavily
        # These are usually synthetic combinations, not real dictionary words
        for prefix in self.PRODUCTIVE_PREFIXES:
            if word.startswith(prefix) and len(word) > len(prefix) + 3:
                score -= 35
                reasons.append(f"productive prefix compound: {prefix}-")
                break
        
        # Good prefixes (appear in real words)
        for prefix in self.REAL_WORD_PREFIXES:
            if word.startswith(prefix) and len(word) > len(prefix) + 2:
                if length <= 10:  # Only reward short words with these prefixes
                    score += 5
                    reasons.append(f"real-word prefix: {prefix}-")
                break
        
        # Common suffixes (slight bonus for short words only)
        for suffix in self.SUFFIXES:
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                if length <= 10:  # Only reward short words
                    score += 5
                    reasons.append(f"common suffix: -{suffix}")
                break
        
        # Vowel/consonant balance
        vowels = sum(1 for c in word if c in 'aeiou')
        if length > 0 and 0.25 <= vowels / length <= 0.5:
            score += 10
            reasons.append("good vowel balance")
        elif length > 0:
            score -= 10
            reasons.append("poor vowel balance")
        
        # First letter frequency bonus
        if word[0] in 'stcpbdmrahfglewn':  # Common starting letters
            score += 5
            reasons.append("common starting letter")
        
        # Bonus for simple structure (no repeated patterns)
        if len(set(word)) >= len(word) * 0.6:  # Good letter diversity
            score += 5
            reasons.append("good letter diversity")
        
        # Clamp score to 0-100
        score = max(0, min(100, score))
        
        return CandidateWord(word=word, score=score, reasons=reasons)
    
    def prioritize_words(
        self, 
        words: list[str], 
        limit: int = 1000
    ) -> list[CandidateWord]:
        """
        Pre-filter and score words, with randomization within score tiers.
        
        First applies strict pre-filtering to eliminate obviously non-English words,
        then scores and samples from remaining candidates.
        
        Args:
            words: List of words to score
            limit: Maximum number to return
            
        Returns:
            Top candidates with randomization within score tiers
        """
        logger.info(f"Pre-filtering {len(words)} words...")
        
        # Pre-filter to likely English words
        likely_english = [w for w in words if self.is_likely_english(w)]
        logger.info(f"  Passed pre-filter: {len(likely_english)} words ({100*len(likely_english)/len(words):.1f}%)")
        
        # If we have enough candidates, sample randomly first to avoid scoring all 9M
        if len(likely_english) > limit * 10:
            sample_size = min(len(likely_english), limit * 50)
            likely_english = random.sample(likely_english, sample_size)
            logger.info(f"  Sampled {sample_size} for scoring")
        
        # Score sampled words
        logger.info(f"Scoring {len(likely_english)} words...")
        candidates = [self.score_word(word) for word in likely_english]
        
        # Group by score tiers (every 5 points)
        from collections import defaultdict
        tiers = defaultdict(list)
        for c in candidates:
            tier = int(c.score // 5) * 5  # 0-4 -> 0, 5-9 -> 5, etc.
            tiers[tier].append(c)
        
        # Build result: take from highest tiers first, shuffle within each tier
        result = []
        for tier in sorted(tiers.keys(), reverse=True):
            tier_candidates = tiers[tier]
            random.shuffle(tier_candidates)  # Randomize within tier
            
            needed = limit - len(result)
            if needed <= 0:
                break
            result.extend(tier_candidates[:needed])
        
        logger.info(f"Selected {len(result)} candidates from score tiers "
                   f"{min(tiers.keys())}-{max(tiers.keys())}")
        
        return result


class InvalidListValidator:
    """
    Validates words from the invalid list against dictionary APIs.
    """
    
    def __init__(self):
        self.api_client = DictionaryAPIClient(use_medical=True)
        self.word_validator = WordValidator()
        self.prioritizer = WordPrioritizer()
        
        # Track progress
        self.progress_file = PHASE3_ROOT / "validation_progress.json"
        self.validated_words: set = set()
        self.promoted_words: list = []
        
    def load_progress(self) -> dict:
        """Load validation progress from disk."""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            "validated_count": 0,
            "promoted_count": 0,
            "last_run": None,
            "validated_words": []
        }
    
    def save_progress(self, progress: dict):
        """Save validation progress to disk."""
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
    
    def load_invalid_words(self) -> list[str]:
        """Load invalid words that haven't been validated yet."""
        progress = self.load_progress()
        already_validated = set(progress.get("validated_words", []))
        
        if not INVALID_WORDS_FILE.exists():
            logger.error(f"Invalid words file not found: {INVALID_WORDS_FILE}")
            return []
        
        logger.info(f"Loading invalid words from {INVALID_WORDS_FILE}")
        
        with open(INVALID_WORDS_FILE, 'r', encoding='utf-8') as f:
            all_words = [line.strip() for line in f if line.strip()]
        
        # Filter out already validated
        remaining = [w for w in all_words if w not in already_validated]
        
        logger.info(f"Total invalid words: {len(all_words)}")
        logger.info(f"Already validated: {len(already_validated)}")
        logger.info(f"Remaining to validate: {len(remaining)}")
        
        return remaining
    
    def load_valid_words(self) -> set[str]:
        """Load current valid words."""
        if not VALID_WORDS_FILE.exists():
            return set()
        
        with open(VALID_WORDS_FILE, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    
    async def validate_batch(
        self, 
        words: list[str]
    ) -> tuple[list[str], list[str]]:
        """
        Validate a batch of words.
        
        Returns:
            Tuple of (valid_words, still_invalid_words)
        """
        valid = []
        still_invalid = []
        
        for word in words:
            # First check basic rules
            rule_result = self.word_validator.validate(word)
            if not rule_result.is_valid:
                still_invalid.append(word)
                continue
            
            # Check dictionary API
            result = await self.api_client.lookup_word(word)
            
            if result.status == WordStatus.VALID:
                valid.append(word)
                logger.info(f"✅ PROMOTED: {word} ({result.source})")
            elif result.status == WordStatus.PROPER_NOUN:
                still_invalid.append(word)
                logger.debug(f"❌ Proper noun: {word}")
            else:
                still_invalid.append(word)
        
        return valid, still_invalid
    
    async def run_daily_validation(
        self, 
        limit: int = None,
        sample_mode: bool = False
    ) -> dict:
        """
        Run daily validation of invalid list.
        
        Args:
            limit: Maximum words to validate (default: DAILY_VALIDATION_LIMIT)
            sample_mode: If True, sample randomly instead of prioritizing
            
        Returns:
            Dictionary with validation results
        """
        limit = limit or DAILY_VALIDATION_LIMIT
        
        logger.info("=" * 60)
        logger.info("Invalid List Validation - Daily Run")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        # Load data
        invalid_words = self.load_invalid_words()
        valid_words = self.load_valid_words()
        progress = self.load_progress()
        
        if not invalid_words:
            logger.info("No more words to validate!")
            return {
                "success": True, 
                "promoted": 0, 
                "validated": 0, 
                "promoted_words": [],
                "message": "No invalid words file found or all words already validated"
            }
        
        # Select candidates
        if sample_mode:
            # Random sampling
            candidates = random.sample(
                invalid_words, 
                min(limit, len(invalid_words))
            )
            logger.info(f"Randomly sampled {len(candidates)} words")
        else:
            # Prioritized selection
            prioritized = self.prioritizer.prioritize_words(invalid_words, limit)
            candidates = [c.word for c in prioritized]
            logger.info(f"Selected top {len(candidates)} priority candidates")
            
            # Log top 10 scores
            for c in prioritized[:10]:
                logger.debug(f"  {c.word}: {c.score:.1f} ({', '.join(c.reasons[:2])})")
        
        # Validate in batches
        all_valid = []
        all_still_invalid = []
        
        for i in range(0, len(candidates), VALIDATION_BATCH_SIZE):
            batch = candidates[i:i + VALIDATION_BATCH_SIZE]
            logger.info(f"Validating batch {i // VALIDATION_BATCH_SIZE + 1} ({len(batch)} words)...")
            
            valid, still_invalid = await self.validate_batch(batch)
            all_valid.extend(valid)
            all_still_invalid.extend(still_invalid)
        
        # Update progress
        progress["validated_words"].extend(candidates)
        progress["validated_count"] += len(candidates)
        progress["promoted_count"] += len(all_valid)
        progress["last_run"] = datetime.now().isoformat()
        self.save_progress(progress)
        
        # Calculate results
        duration = (datetime.now() - start_time).total_seconds()
        
        results = {
            "success": True,
            "date": get_release_date(),
            "validated": len(candidates),
            "promoted": len(all_valid),
            "promoted_words": all_valid,
            "still_invalid": len(all_still_invalid),
            "duration_seconds": duration,
            "total_validated": progress["validated_count"],
            "total_promoted": progress["promoted_count"],
            "remaining": len(invalid_words) - len(candidates)
        }
        
        # Summary
        logger.info("=" * 60)
        logger.info("VALIDATION COMPLETE")
        logger.info(f"  Words validated: {results['validated']}")
        logger.info(f"  Words promoted: {results['promoted']}")
        logger.info(f"  Promotion rate: {results['promoted'] / results['validated'] * 100:.2f}%")
        logger.info(f"  Duration: {duration:.1f}s")
        logger.info(f"  Remaining to validate: {results['remaining']:,}")
        logger.info("=" * 60)
        
        if all_valid:
            logger.info("Promoted words:")
            for word in all_valid:
                logger.info(f"  + {word}")
        
        return results
    
    def save_promoted_words(self, promoted_words: list[str]):
        """Save promoted words to the output directory."""
        if not promoted_words:
            return
        
        output_dir = OUTPUT_DIR / get_release_date()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to file
        promoted_file = output_dir / "promoted_words.txt"
        with open(promoted_file, 'a', encoding='utf-8') as f:
            for word in promoted_words:
                f.write(f"{word}\n")
        
        logger.info(f"Saved {len(promoted_words)} promoted words to {promoted_file}")


async def main():
    """Main entry point for invalid list validation."""
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    parser = argparse.ArgumentParser(description="Validate invalid word list")
    parser.add_argument("--limit", type=int, default=None, 
                        help=f"Words to validate (default: {DAILY_VALIDATION_LIMIT})")
    parser.add_argument("--sample", action="store_true",
                        help="Use random sampling instead of prioritization")
    parser.add_argument("--reset", action="store_true",
                        help="Reset validation progress")
    args = parser.parse_args()
    
    validator = InvalidListValidator()
    
    if args.reset:
        if validator.progress_file.exists():
            validator.progress_file.unlink()
            print("Progress reset.")
    
    results = await validator.run_daily_validation(
        limit=args.limit,
        sample_mode=args.sample
    )
    
    # Save promoted words if any were found
    if results.get("promoted_words"):
        validator.save_promoted_words(results["promoted_words"])
    
    # Return exit code 0 even if no words to validate (graceful handling)
    return results


if __name__ == "__main__":
    asyncio.run(main())
