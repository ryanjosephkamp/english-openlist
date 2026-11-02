"""
Tests for Word Validator
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.word_validator import WordValidator, ValidationResult


class TestWordValidator:
    """Test cases for WordValidator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = WordValidator()
    
    # === Valid word tests ===
    
    def test_valid_simple_word(self):
        """Test that a simple lowercase word is valid."""
        result = self.validator.validate("hello")
        assert result.is_valid is True
        assert result.word == "hello"
    
    def test_valid_two_letter_word(self):
        """Test minimum length word."""
        result = self.validator.validate("hi")
        assert result.is_valid is True
    
    def test_valid_long_word(self):
        """Test a long but valid word."""
        result = self.validator.validate("supercalifragilisticexpialidocious")
        assert result.is_valid is True
    
    # === Invalid word tests ===
    
    def test_invalid_uppercase(self):
        """Test that uppercase letters are rejected."""
        result = self.validator.validate("HELLO")
        assert result.is_valid is False
        assert "uppercase" in result.reason.lower()
    
    def test_invalid_mixed_case(self):
        """Test that mixed case is rejected."""
        result = self.validator.validate("Hello")
        assert result.is_valid is False
    
    def test_invalid_numbers(self):
        """Test that numbers are rejected."""
        result = self.validator.validate("hello123")
        assert result.is_valid is False
        assert "non-alphabetic" in result.reason.lower()
    
    def test_invalid_hyphen(self):
        """Test that hyphens are rejected."""
        result = self.validator.validate("hello-world")
        assert result.is_valid is False
    
    def test_invalid_space(self):
        """Test that spaces are rejected."""
        result = self.validator.validate("hello world")
        assert result.is_valid is False
    
    def test_single_letter_a_is_valid(self):
        """`a` is a word. The 2-character floor that excluded it was a Scrabble
        convention, removed 2026-08-16 — see D-025."""
        result = self.validator.validate("a")
        assert result.is_valid is True
        assert result.word == "a"

    def test_single_letter_i_is_valid(self):
        """`i` likewise — the pronoun, not the glyph name."""
        result = self.validator.validate("i")
        assert result.is_valid is True

    def test_every_single_letter_passes_the_form_rule(self):
        """All 26 are form-legal. Which of them are *words* is decided by
        evidence, not by this function — D-027."""
        for letter in "abcdefghijklmnopqrstuvwxyz":
            assert self.validator.validate(letter).is_valid is True, letter


    def test_invalid_empty(self):
        """Test that empty strings are rejected."""
        result = self.validator.validate("")
        assert result.is_valid is False
    
    def test_invalid_none(self):
        """Test that None is rejected."""
        result = self.validator.validate(None)
        assert result.is_valid is False
    
    def test_invalid_accented(self):
        """Test that accented characters are rejected."""
        result = self.validator.validate("café")
        assert result.is_valid is False
    
    def test_invalid_apostrophe(self):
        """Test that apostrophes are rejected."""
        result = self.validator.validate("don't")
        assert result.is_valid is False
    
    # === Batch validation tests ===
    
    def test_batch_validation(self):
        """Test batch validation."""
        words = ["hello", "WORLD", "test", "123", "valid"]
        valid, invalid = self.validator.validate_batch(words)
        
        assert "hello" in valid
        assert "test" in valid
        assert "valid" in valid
        assert len(valid) == 3
        assert len(invalid) == 2
    
    # === Edge cases ===
    
    def test_whitespace_trimming(self):
        """Test that whitespace is trimmed."""
        result = self.validator.validate("  hello  ")
        assert result.is_valid is True
        assert result.word == "hello"
    
    def test_forty_five_characters_still_valid(self):
        """The old ceiling. Still fine, just no longer a boundary."""
        assert self.validator.validate("a" * 45).is_valid is True

    def test_attested_46_character_word_is_valid(self):
        """The concrete word the 45-character ceiling was excluding. It carries
        a Wiktionary English entry — D-025."""
        word = "phosphoribosylaminoimidazolesuccinocarboxamide"
        assert len(word) == 46
        assert self.validator.validate(word).is_valid is True

    def test_no_upper_length_bound_at_all(self):
        """Chemical nomenclature is productive, so any ceiling is arbitrary."""
        assert self.validator.validate("a" * 500).is_valid is True

    def test_length_flag_is_not_a_validation_rule(self):
        """A string over the integrity threshold is still form-valid. The flag
        exists to catch concatenation bugs, and must not become a ceiling."""
        from scripts.word_validator import exceeds_length_flag
        long_string = "a" * 150
        assert exceeds_length_flag(long_string) is True
        assert self.validator.validate(long_string).is_valid is True
        assert exceeds_length_flag("a" * 63) is False   # longest real candidate


class TestCustomRules:
    """Test custom validation rules."""
    
    def test_custom_min_length(self):
        """Test custom minimum length."""
        validator = WordValidator(rules={"min_length": 5})
        
        result = validator.validate("hi")
        assert result.is_valid is False
        
        result = validator.validate("hello")
        assert result.is_valid is True
    
    def test_allow_uppercase(self):
        """Test allowing uppercase letters."""
        validator = WordValidator(rules={"lowercase_only": False})
        
        result = validator.validate("HELLO")
        assert result.is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
