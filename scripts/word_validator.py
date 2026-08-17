"""
Word Validator
Validates words against the English OpenList form rules.

The whole rule is ``^[a-z]+$``. There is no length bound.

**This is deliberately not Scrabble-compatible**, as of 2026-08-16. The list had
inherited a 2-character minimum and a 45-character maximum from Scrabble
tournament dictionaries, and both excluded strings that are words of English:

* the minimum excluded ``a`` and ``i``. No Scrabble list can hold them — ENABLE,
  SOWPODS, NWL2023 and CSW21 have zero one-letter entries between them.
* the maximum excluded ``phosphoribosylaminoimidazolesuccinocarboxamide``, which
  is 46 characters and carries a Wiktionary English entry. Chemical nomenclature
  is productive and unbounded, so any numeric ceiling is arbitrary.

Removing the ceiling admits nothing unwanted: the over-length strings that were
being caught are Welsh, Māori and Fijian place names, and they are excluded for
being proper nouns, which is what should have been excluding them all along.

``config.LENGTH_FLAG_OVER`` replaces the ceiling with an *integrity* check —
a guard against concatenation bugs, not a statement about wordhood.

See PROTOCOL.md §1.3 and research/DECISIONS.md D-025.

Rules:
1. Lowercase letters only (a-z)
2. No proper nouns
3. No abbreviations or acronyms (handled via dictionary API)
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

    Default rules:
    - Lowercase alphabetic characters only
    - No proper nouns
    - No length bound (see the module docstring for why)
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
        
        # Length bounds are only applied if a caller asks for them explicitly.
        # The default rules carry neither: see the module docstring and D-025.
        min_length = self.rules.get("min_length")
        if min_length is not None and len(word) < min_length:
            return ValidationResult(
                word=original_word,
                is_valid=False,
                reason=f"Too short (min {min_length} characters)"
            )

        max_length = self.rules.get("max_length")
        if max_length is not None and len(word) > max_length:
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


def exceeds_length_flag(word: str, threshold: Optional[int] = None) -> bool:
    """
    Ingest integrity check, not a validation rule.

    A candidate this long is far more likely to be a concatenation bug — lost
    spaces during a scan, a field boundary crossed — than a word. It is flagged
    for a recorded reason rather than rejected, because the rule change of
    2026-08-16 deliberately removed the length ceiling and this must not
    reintroduce one by the back door.

    Nothing in the candidate universe currently trips it; the longest string is
    63 characters.
    """
    if threshold is None:
        from config import LENGTH_FLAG_OVER
        threshold = LENGTH_FLAG_OVER
    return len(word or "") > threshold


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
        "a",           # Valid since 2026-08-16 — the indefinite article
        "i",           # Valid since 2026-08-16 — the pronoun
        "hi",          # Valid
        "supercalifragilisticexpialidocious",  # Valid
        # 46 characters, attested in Wiktionary. Valid since 2026-08-16; the
        # 45-character Scrabble ceiling was the only thing excluding it.
        "phosphoribosylaminoimidazolesuccinocarboxamide",
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
