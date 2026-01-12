"""
Data Updater
Handles updating the Valid and Invalid word lists and dictionaries.

This module:
- Loads existing data from Phase 1-2 deliverables
- Adds newly validated words to the Valid list
- Removes promoted words from the Invalid list
- Maintains dictionary metadata
- Saves updated data
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
import orjson

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    VALID_WORDS_FILE, VALID_DICT_FILE,
    INVALID_WORDS_FILE, INVALID_DICT_FILE,
    get_release_dir
)

logger = logging.getLogger(__name__)


@dataclass
class UpdateStats:
    """Statistics for a data update operation."""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    words_added_to_valid: int = 0
    words_removed_from_invalid: int = 0
    total_valid_before: int = 0
    total_valid_after: int = 0
    total_invalid_before: int = 0
    total_invalid_after: int = 0
    new_words: list = field(default_factory=list)
    promoted_words: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "words_added_to_valid": self.words_added_to_valid,
            "words_removed_from_invalid": self.words_removed_from_invalid,
            "total_valid_before": self.total_valid_before,
            "total_valid_after": self.total_valid_after,
            "total_invalid_before": self.total_invalid_before,
            "total_invalid_after": self.total_invalid_after,
            "new_words": self.new_words,
            "promoted_words": self.promoted_words,
            "errors": self.errors,
        }


class DataManager:
    """
    Manages loading and saving of word lists and dictionaries.
    
    Handles both the merged files and alphabetized subsets.
    """
    
    def __init__(
        self,
        valid_words_path: Optional[Path] = None,
        valid_dict_path: Optional[Path] = None,
        invalid_words_path: Optional[Path] = None,
        invalid_dict_path: Optional[Path] = None,
        skip_invalid: bool = False
    ):
        self.valid_words_path = valid_words_path or VALID_WORDS_FILE
        self.valid_dict_path = valid_dict_path or VALID_DICT_FILE
        self.invalid_words_path = invalid_words_path or INVALID_WORDS_FILE
        self.invalid_dict_path = invalid_dict_path or INVALID_DICT_FILE
        self.skip_invalid = skip_invalid
        
        # Loaded data
        self.valid_words: set = set()
        self.valid_dict: dict = {}
        self.invalid_words: set = set()
        self.invalid_dict: dict = {}
        
        self._loaded = False
    
    def load_data(self) -> None:
        """Load all data from files."""
        logger.info("Loading existing word data...")
        
        # Load valid words list
        if self.valid_words_path.exists():
            with open(self.valid_words_path, 'r', encoding='utf-8') as f:
                self.valid_words = set(line.strip() for line in f if line.strip())
            logger.info(f"Loaded {len(self.valid_words)} valid words")
        else:
            logger.warning(f"Valid words file not found: {self.valid_words_path}")
        
        # Load valid dictionary
        if self.valid_dict_path.exists():
            with open(self.valid_dict_path, 'rb') as f:
                self.valid_dict = orjson.loads(f.read())
            logger.info(f"Loaded valid dictionary with {len(self.valid_dict)} entries")
        else:
            logger.warning(f"Valid dict file not found: {self.valid_dict_path}")
        
        # Skip loading invalid words if flag is set (for testing/memory constraints)
        if self.skip_invalid:
            logger.info("Skipping invalid words loading (skip_invalid=True)")
            self._loaded = True
            return
        
        # Load invalid words list (memory-efficient: count lines first)
        if self.invalid_words_path.exists():
            # For very large files, just count and keep path for reference
            with open(self.invalid_words_path, 'r', encoding='utf-8') as f:
                self.invalid_words = set(line.strip() for line in f if line.strip())
            logger.info(f"Loaded {len(self.invalid_words)} invalid words")
        else:
            logger.warning(f"Invalid words file not found: {self.invalid_words_path}")
        
        # Load invalid dictionary (this can be large, use streaming if needed)
        if self.invalid_dict_path.exists():
            try:
                with open(self.invalid_dict_path, 'rb') as f:
                    self.invalid_dict = orjson.loads(f.read())
                logger.info(f"Loaded invalid dictionary with {len(self.invalid_dict)} entries")
            except Exception as e:
                logger.warning(f"Could not load invalid dict (may be too large): {e}")
                self.invalid_dict = {}
        else:
            logger.warning(f"Invalid dict file not found: {self.invalid_dict_path}")
        
        self._loaded = True
    
    def save_data(self, output_dir: Optional[Path] = None) -> None:
        """
        Save all data to files.
        
        Args:
            output_dir: Directory to save to. Uses release dir if not specified.
        """
        output_dir = output_dir or get_release_dir()
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving updated data to {output_dir}")
        
        # Save valid words list (sorted)
        valid_words_file = output_dir / "merged_valid_words.txt"
        with open(valid_words_file, 'w', encoding='utf-8') as f:
            for word in sorted(self.valid_words):
                f.write(f"{word}\n")
        logger.info(f"Saved {len(self.valid_words)} valid words")
        
        # Save valid dictionary
        valid_dict_file = output_dir / "merged_valid_dict.json"
        with open(valid_dict_file, 'wb') as f:
            f.write(orjson.dumps(self.valid_dict, option=orjson.OPT_INDENT_2))
        logger.info(f"Saved valid dictionary")
        
        # Save invalid words list (sorted)
        invalid_words_file = output_dir / "merged_invalid_words.txt"
        with open(invalid_words_file, 'w', encoding='utf-8') as f:
            for word in sorted(self.invalid_words):
                f.write(f"{word}\n")
        logger.info(f"Saved {len(self.invalid_words)} invalid words")
        
        # Save invalid dictionary
        invalid_dict_file = output_dir / "merged_invalid_dict.json"
        with open(invalid_dict_file, 'wb') as f:
            f.write(orjson.dumps(self.invalid_dict, option=orjson.OPT_INDENT_2))
        logger.info(f"Saved invalid dictionary")
    
    def add_valid_word(
        self,
        word: str,
        metadata: Optional[dict] = None
    ) -> bool:
        """
        Add a word to the valid list.
        
        Args:
            word: The word to add
            metadata: Optional metadata for the dictionary entry
            
        Returns:
            True if word was added (wasn't already present)
        """
        word = word.lower().strip()
        
        if word in self.valid_words:
            return False
        
        self.valid_words.add(word)
        
        # Add dictionary entry
        if metadata:
            self.valid_dict[word] = metadata
        else:
            self.valid_dict[word] = {
                "word": word,
                "source": "phase3_update",
                "added_date": datetime.now().isoformat(),
                "validation_status": "valid"
            }
        
        return True
    
    def remove_from_invalid(self, word: str) -> bool:
        """
        Remove a word from the invalid list.
        
        Args:
            word: The word to remove
            
        Returns:
            True if word was removed (was present)
        """
        word = word.lower().strip()
        
        if word not in self.invalid_words:
            return False
        
        self.invalid_words.discard(word)
        
        # Remove dictionary entry if present
        if word in self.invalid_dict:
            del self.invalid_dict[word]
        
        return True


class DataUpdater:
    """
    Orchestrates updates to the word data.
    
    Handles the full update workflow:
    1. Load existing data
    2. Apply new words
    3. Remove promoted words from invalid
    4. Generate statistics
    5. Save updated data
    """
    
    def __init__(self, data_manager: Optional[DataManager] = None):
        self.data_manager = data_manager or DataManager()
        self.stats = UpdateStats()
    
    def run_update(
        self,
        new_valid_words: list[dict],
        output_dir: Optional[Path] = None
    ) -> UpdateStats:
        """
        Run a full update cycle.
        
        Args:
            new_valid_words: List of dicts with 'word' and optional metadata
            output_dir: Directory to save updated data
            
        Returns:
            UpdateStats with summary of changes
        """
        logger.info("Starting data update...")
        
        # Load existing data
        self.data_manager.load_data()
        
        # Record initial counts
        self.stats.total_valid_before = len(self.data_manager.valid_words)
        self.stats.total_invalid_before = len(self.data_manager.invalid_words)
        
        # Process new words
        for entry in new_valid_words:
            word = entry.get("word", "").lower().strip()
            if not word:
                continue
            
            metadata = entry.get("metadata", {})
            
            # Add to valid list
            if self.data_manager.add_valid_word(word, metadata):
                self.stats.words_added_to_valid += 1
                self.stats.new_words.append(word)
                logger.debug(f"Added new valid word: {word}")
            
            # Remove from invalid list if present
            if self.data_manager.remove_from_invalid(word):
                self.stats.words_removed_from_invalid += 1
                self.stats.promoted_words.append(word)
                logger.debug(f"Promoted word from invalid: {word}")
        
        # Record final counts
        self.stats.total_valid_after = len(self.data_manager.valid_words)
        self.stats.total_invalid_after = len(self.data_manager.invalid_words)
        
        # Save updated data
        self.data_manager.save_data(output_dir)
        
        logger.info(f"Update complete: +{self.stats.words_added_to_valid} valid, "
                   f"-{self.stats.words_removed_from_invalid} invalid")
        
        return self.stats


def create_word_metadata(
    word: str,
    source: str = "phase3_update",
    part_of_speech: Optional[str] = None,
    definition: Optional[str] = None,
    pronunciation: Optional[str] = None,
    etymology: Optional[str] = None
) -> dict:
    """
    Create a metadata dictionary for a word entry.
    
    Args:
        word: The word
        source: Source of the word (e.g., "merriam-webster")
        part_of_speech: Part of speech (noun, verb, etc.)
        definition: Word definition
        pronunciation: Phonetic pronunciation
        etymology: Word etymology
        
    Returns:
        Dictionary with word metadata
    """
    return {
        "word": word,
        "source": source,
        "added_date": datetime.now().isoformat(),
        "validation_status": "valid",
        "part_of_speech": part_of_speech,
        "definition": definition,
        "pronunciation": pronunciation,
        "etymology": etymology,
    }


if __name__ == "__main__":
    # Test the data updater
    import tempfile
    
    # Create test data
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Create test valid words file
        valid_words = tmpdir / "valid_words.txt"
        with open(valid_words, 'w') as f:
            f.write("apple\nbanana\ncherry\n")
        
        # Create test valid dict
        valid_dict = tmpdir / "valid_dict.json"
        with open(valid_dict, 'w') as f:
            json.dump({"apple": {"word": "apple"}, "banana": {"word": "banana"}}, f)
        
        # Create test invalid words file
        invalid_words = tmpdir / "invalid_words.txt"
        with open(invalid_words, 'w') as f:
            f.write("boba\nfurikake\nxyzzy\n")
        
        # Create test invalid dict
        invalid_dict = tmpdir / "invalid_dict.json"
        with open(invalid_dict, 'w') as f:
            json.dump({"boba": {"word": "boba"}, "furikake": {"word": "furikake"}}, f)
        
        # Create data manager
        dm = DataManager(
            valid_words_path=valid_words,
            valid_dict_path=valid_dict,
            invalid_words_path=invalid_words,
            invalid_dict_path=invalid_dict
        )
        
        # Run update
        updater = DataUpdater(dm)
        
        new_words = [
            {"word": "boba", "metadata": {"source": "merriam-webster"}},
            {"word": "mango", "metadata": {"source": "merriam-webster"}},
        ]
        
        stats = updater.run_update(new_words, tmpdir / "output")
        
        print("\nUpdate Statistics:")
        print(f"  Words added to valid: {stats.words_added_to_valid}")
        print(f"  Words removed from invalid: {stats.words_removed_from_invalid}")
        print(f"  New words: {stats.new_words}")
        print(f"  Promoted words: {stats.promoted_words}")
