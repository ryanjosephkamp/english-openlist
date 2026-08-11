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
    
    def test_invalid_too_short(self):
        """Test that single letters are rejected."""
        result = self.validator.validate("a")
        assert result.is_valid is False
        assert "too short" in result.reason.lower()
    
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
    
    def test_exactly_max_length(self):
        """Test word at exactly max length."""
        word = "a" * 45
        result = self.validator.validate(word)
        assert result.is_valid is True
    
    def test_exceeds_max_length(self):
        """Test word exceeding max length."""
        word = "a" * 46
        result = self.validator.validate(word)
        assert result.is_valid is False
        assert "too long" in result.reason.lower()


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
