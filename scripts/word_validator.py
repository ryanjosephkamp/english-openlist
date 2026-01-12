"""
Word Validator
Validates words against Scrabble-compatible rules.

Rules:
1. Lowercase letters only (a-z)
2. No proper nouns
3. Minimum length of 2 characters
4. Maximum length of 45 characters
5. No abbreviations or acronyms (handled via dictionary API)
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import VALIDATION_RULES

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of word validation."""
    word: str
    is_valid: bool
    reason: Optional[str] = None


class WordValidator:
    """
    Validates words against configurable rules.
    
    Default rules follow Scrabble guidelines:
    - Lowercase alphabetic characters only
    - No proper nouns
    - Length between 2 and 45 characters
    """
    
    def __init__(self, rules: Optional[dict] = None):
        """
        Initialize validator with rules.
        
        Args:
            rules: Dictionary of validation rules. Uses defaults if not provided.
        """
        self.rules = rules or VALIDATION_RULES
        
        # Compile regex patterns based on rules
        if self.rules.get("lowercase_only", True):
            self.alphabetic_pattern = re.compile(r'^[a-z]+$')
        else:
            self.alphabetic_pattern = re.compile(r'^[a-zA-Z]+$')
    
    def validate(self, word: str) -> ValidationResult:
        """
        Validate a single word.
        
        Args:
            word: The word to validate
            
        Returns:
            ValidationResult with is_valid status and reason if invalid
        """
        # Check if word is None or empty
        if not word:
            return ValidationResult(
                word=word or "",
                is_valid=False,
                reason="Empty or None word"
            )
        
        original_word = word
        
        # Normalize to lowercase for comparison
        word = word.strip()
        
        # Check lowercase requirement
        if self.rules.get("lowercase_only", True):
            if word != word.lower():
                return ValidationResult(
                    word=original_word,
                    is_valid=False,
                    reason="Contains uppercase letters (potential proper noun)"
                )
            word = word.lower()
        
        # Check alphabetic requirement
        if self.rules.get("alphabetic_only", True):
            if not self.alphabetic_pattern.match(word):
                return ValidationResult(
                    word=original_word,
                    is_valid=False,
                    reason="Contains non-alphabetic characters"
                )
        
        # Check minimum length
        min_length = self.rules.get("min_length", 2)
        if len(word) < min_length:
            return ValidationResult(
                word=original_word,
                is_valid=False,
                reason=f"Too short (min {min_length} characters)"
            )
        
        # Check maximum length
        max_length = self.rules.get("max_length", 45)
        if len(word) > max_length:
            return ValidationResult(
                word=original_word,
                is_valid=False,
                reason=f"Too long (max {max_length} characters)"
            )
        
        # All checks passed
        return ValidationResult(
            word=word,
            is_valid=True
        )
    
    def validate_batch(self, words: list[str]) -> tuple[list[str], list[ValidationResult]]:
        """
        Validate a batch of words.
        
        Args:
            words: List of words to validate
            
        Returns:
            Tuple of (valid_words, invalid_results)
        """
        valid_words = []
        invalid_results = []
        
        for word in words:
            result = self.validate(word)
            if result.is_valid:
                valid_words.append(result.word)
            else:
                invalid_results.append(result)
        
        return valid_words, invalid_results
    
    def is_potential_proper_noun(self, word: str) -> bool:
        """
        Heuristic check for potential proper nouns.
        
        This is a simple check based on capitalization.
        For more accurate detection, use the dictionary API.
        
        Args:
            word: The word to check
            
        Returns:
            True if word might be a proper noun
        """
        if not word:
            return False
        
        # Check if first letter is uppercase
        if word[0].isupper():
            return True
        
        # Check for mixed case (e.g., "iPhone")
        if any(c.isupper() for c in word[1:]):
            return True
        
        return False


class ProperNounDetector:
    """
    Detects proper nouns using multiple heuristics.
    
    Methods:
    1. Capitalization patterns
    2. Common proper noun suffixes/prefixes
    3. Dictionary API metadata
    """
    
    # Common proper noun patterns
    PROPER_NOUN_PATTERNS = [
        # Geographic suffixes
        r'.+shire$',
        r'.+land$',
        r'.+stan$',
        r'.+ville$',
        r'.+burg$',
        r'.+ton$',
        
        # Name patterns
        r'^mc.+$',
        r'^mac.+$',
        r'^o\'.+$',
    ]
    
    # Common words that look like proper nouns but aren't
    FALSE_POSITIVE_PATTERNS = [
        'highland', 'lowland', 'mainland', 'homeland', 'woodland',
        'farmland', 'grassland', 'wasteland', 'wetland',
        'washington',  # When used as verb "to washington"
    ]
    
    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.PROPER_NOUN_PATTERNS]
    
    def is_likely_proper_noun(self, word: str) -> bool:
        """
        Determine if a word is likely a proper noun.
        
        Args:
            word: The word to check
            
        Returns:
            True if likely a proper noun
        """
        if not word:
            return False
        
        word_lower = word.lower()
        
        # Check false positives first
        if word_lower in self.FALSE_POSITIVE_PATTERNS:
            return False
        
        # Check capitalization
        if word[0].isupper():
            return True
        
        # Note: Pattern matching for lowercase words is tricky
        # because many valid words match these patterns.
        # We rely primarily on the dictionary API for proper noun detection.
        
        return False


def validate_new_word(
    word: str,
    existing_valid_words: set[str],
    existing_invalid_words: set[str]
) -> tuple[bool, str]:
    """
    Validate a potential new word for addition to the valid list.
    
    Args:
        word: The word to validate
        existing_valid_words: Set of current valid words
        existing_invalid_words: Set of current invalid words
        
    Returns:
        Tuple of (is_new_valid_word, reason)
    """
    validator = WordValidator()
    
    # Basic validation
    result = validator.validate(word)
    if not result.is_valid:
        return False, result.reason
    
    normalized_word = result.word
    
    # Check if already in valid list
    if normalized_word in existing_valid_words:
        return False, "Already in valid word list"
    
    # Word passes all checks - it's a valid new word
    return True, "New valid word"


if __name__ == "__main__":
    # Test the validator
    validator = WordValidator()
    
    test_words = [
        "hello",       # Valid
        "HELLO",       # Invalid (uppercase)
        "Hello",       # Invalid (mixed case)
        "hello123",    # Invalid (numbers)
        "hello-world", # Invalid (hyphen)
        "a",           # Invalid (too short)
        "hi",          # Valid (min length)
        "supercalifragilisticexpialidocious",  # Valid (long but OK)
        "",            # Invalid (empty)
        "café",        # Invalid (non-ASCII)
    ]
    
    print("Word Validation Tests:")
    print("-" * 50)
    
    for word in test_words:
        result = validator.validate(word)
        status = "✓ VALID" if result.is_valid else "✗ INVALID"
        reason = f" ({result.reason})" if result.reason else ""
        print(f"  '{word}': {status}{reason}")
