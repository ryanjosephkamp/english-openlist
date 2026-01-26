"""
Phase 3 Configuration
English OpenList - Automated Dictionary Updates

This file contains configuration settings for the Phase 3 update pipeline.
Sensitive values (API keys) should be set via environment variables.
"""

import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(Path(__file__).parent / ".env")

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

# Base paths
PHASE3_ROOT = Path(__file__).parent
PROJECT_ROOT = PHASE3_ROOT.parent
INITIAL_DELIVERABLES = PHASE3_ROOT / "initial_deliverables"
SCRIPTS_DIR = PHASE3_ROOT / "scripts"
OUTPUT_DIR = PHASE3_ROOT / "output"
TEMPLATES_DIR = PHASE3_ROOT / "templates"

# Input files (from Phases 1-2)
VALID_WORDS_FILE = INITIAL_DELIVERABLES / "merged_valid_words.txt"
VALID_DICT_FILE = INITIAL_DELIVERABLES / "merged_valid_dict.json"
INVALID_WORDS_FILE = INITIAL_DELIVERABLES / "merged_invalid_words.txt"
INVALID_DICT_FILE = INITIAL_DELIVERABLES / "merged_invalid_dict.json"
ALPHABETIZED_DIR = INITIAL_DELIVERABLES / "alphabetized_data"

# =============================================================================
# API CONFIGURATION
# =============================================================================

# Merriam-Webster Collegiate Dictionary API
MW_API_KEY = os.environ.get("MW_API_KEY", "")
MW_BASE_URL = "https://www.dictionaryapi.com/api/v3/references/collegiate/json"
MW_RATE_LIMIT = 1000  # requests per day
MW_REQUEST_DELAY = 0.1  # seconds between requests

# Merriam-Webster Medical Dictionary API
MW_MEDICAL_API_KEY = os.environ.get("MW_MEDICAL_API_KEY", "")
MW_MEDICAL_BASE_URL = "https://www.dictionaryapi.com/api/v3/references/medical/json"

# Free Dictionary API (fallback)
FREE_DICT_BASE_URL = "https://api.dictionaryapi.dev/api/v2/entries/en"

# Wordnik API (optional, for new word discovery)
WORDNIK_API_KEY = os.environ.get("WORDNIK_API_KEY", "")
WORDNIK_BASE_URL = "https://api.wordnik.com/v4/words.json"

# =============================================================================
# HUGGING FACE CONFIGURATION
# =============================================================================

HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_DATASET_REPO = "ryanjosephkamp/english-openlist"  # Format: username/repo
HF_DATASET_PRIVATE = False

# =============================================================================
# UPDATE PIPELINE CONFIGURATION
# =============================================================================

# Validation rules (Scrabble-compatible)
VALIDATION_RULES = {
    "lowercase_only": True,
    "alphabetic_only": True,
    "no_proper_nouns": True,
    "min_length": 2,
    "max_length": 45,  # Longest English word is ~45 chars
}

# Scheduling
UPDATE_SCHEDULE = "daily"  # "daily" or "weekly"
UPDATE_HOUR = 0  # Hour (UTC) for scheduled updates

# Invalid list validation settings
DAILY_VALIDATION_LIMIT = 1000  # Words to validate per day from invalid list
VALIDATION_BATCH_SIZE = 50  # Words per batch for API calls

# =============================================================================
# OUTPUT CONFIGURATION
# =============================================================================

# File naming
def get_release_date() -> str:
    """Get current date in YYYY-MM-DD format for release naming."""
    return datetime.now().strftime("%Y-%m-%d")

def get_release_dir() -> Path:
    """Get the output directory for current release."""
    release_dir = OUTPUT_DIR / get_release_date()
    release_dir.mkdir(parents=True, exist_ok=True)
    return release_dir

# Zip file names
ZIP_VALID_TEMPLATE = "english_openlist_valid_{date}.zip"
ZIP_INVALID_TEMPLATE = "english_openlist_invalid_{date}.zip"
ZIP_CHANGELOG_TEMPLATE = "english_openlist_changelog_{date}.zip"
ZIP_STATS_TEMPLATE = "english_openlist_statistics_{date}.zip"

# =============================================================================
# STATISTICS CONFIGURATION
# =============================================================================

STATS_FIGURES = {
    "word_length_distribution": True,
    "part_of_speech_breakdown": True,
    "words_added_over_time": True,
    "letter_frequency": True,
}

FIGURE_DPI = 150
FIGURE_FORMAT = "png"

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = PHASE3_ROOT / "logs" / "update_pipeline.log"

# =============================================================================
# NEW WORD DISCOVERY SOURCES
# =============================================================================

NEW_WORD_SOURCES = {
    "merriam_webster_rss": "https://www.merriam-webster.com/wotd/feed/rss2",
    "merriam_webster_new_words": "https://www.merriam-webster.com/wordplay/new-words-in-the-dictionary",
    "wordnik_wotd": "https://api.wordnik.com/v4/words.json/wordOfTheDay",
}

# Wordnik API rate limits (Basic/Free plan)
WORDNIK_DAILY_LIMIT = 100  # API calls per day
WORDNIK_WOTD_LOOKBACK_DAYS = 30  # How many days of Word of the Day to fetch

# Discovery tracking (to avoid re-processing same words)
DISCOVERED_WORDS_CACHE = PHASE3_ROOT / "discovered_words_cache.json"

# =============================================================================
# ERROR HANDLING
# =============================================================================

MAX_RETRIES = 3
RETRY_DELAY = 5  # seconds
TIMEOUT = 30  # seconds for API requests
