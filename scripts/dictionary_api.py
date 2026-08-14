"""
Dictionary API Wrapper
Provides unified interface to Merriam-Webster and fallback APIs.

This module handles:
- API authentication
- Rate limiting
- Response parsing
- Proper noun detection
- Error handling with retries
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from enum import Enum

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    MW_API_KEY, MW_BASE_URL, MW_REQUEST_DELAY,
    MW_MEDICAL_API_KEY, MW_MEDICAL_BASE_URL,
    FREE_DICT_BASE_URL, TIMEOUT, MAX_RETRIES, PHASE3_ROOT
)

logger = logging.getLogger(__name__)

# Where cached raw API responses live. Under .cache/ so it is already gitignored,
# alongside .cache/hf.
CACHE_DIR = PHASE3_ROOT / ".cache" / "dictionary"

# The cache is opt-in. The daily pipeline runs unattended and promotes words into
# a published dataset; a stale cached "not found" would quietly freeze a word out
# of promotion for good. So the nightly keeps calling the APIs exactly as it
# always has, and only work that explicitly asks for the cache gets it.
CACHE_ENV_VAR = "EOL_DICT_CACHE"


def cache_enabled() -> bool:
    """True when EOL_DICT_CACHE is set to something meaning yes."""
    return os.environ.get(CACHE_ENV_VAR, "").strip().lower() in {"1", "true", "yes", "on"}


class ResponseCache:
    """
    An append-only JSONL cache of raw dictionary responses, one file per API.

    It stores the *payload*, not the parsed verdict, for two reasons: a verdict
    can then be re-derived offline without spending quota, and a fix to the
    parsing applies retroactively to everything already fetched.

    Disabled unless EOL_DICT_CACHE says otherwise, in which case every read
    misses and every write is dropped.
    """

    def __init__(self, name: str, enabled: Optional[bool] = None):
        self.name = name
        self.enabled = cache_enabled() if enabled is None else enabled
        self.path = CACHE_DIR / f"{name}.jsonl"
        self.hits = 0
        self.misses = 0
        self._entries: dict[str, object] = {}

        if self.enabled:
            self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        bad = 0
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    self._entries[record["word"]] = record["payload"]
                except (json.JSONDecodeError, KeyError):
                    # A half-written final line is the expected way this breaks,
                    # after an interrupted run. Skip it rather than refusing to
                    # start; the word simply gets fetched again.
                    bad += 1
        if bad:
            logger.warning("%s cache: skipped %d unreadable line(s)", self.name, bad)
        logger.info("%s cache: loaded %d entries", self.name, len(self._entries))

    def get(self, word: str):
        """The cached payload, or None for a miss."""
        if not self.enabled:
            return None
        if word in self._entries:
            self.hits += 1
            return self._entries[word]
        self.misses += 1
        return None

    def put(self, word: str, payload, http_status: Optional[int] = None) -> None:
        """Record a payload. Appends, so an interrupted run keeps what it fetched."""
        if not self.enabled:
            return
        self._entries[word] = payload
        self.path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "word": word,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "http_status": http_status,
            "payload": payload,
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


class WordStatus(Enum):
    """Status of a word lookup."""
    VALID = "valid"
    INVALID = "invalid"
    NOT_FOUND = "not_found"
    PROPER_NOUN = "proper_noun"
    ABBREVIATION = "abbreviation"
    ERROR = "error"

    def __str__(self) -> str:
        """
        Render as the value, not as "WordStatus.VALID".

        201 entries in merged_valid_dict.json carried `"status": "WordStatus.VALID"`
        — a member of this enum stringified by a writer that has since been
        replaced. They were repaired on 2026-08-13. No current code path
        stringifies a member, but this makes the accident harmless if one ever
        does again: the value is what belongs in the data either way.
        """
        return self.value


@dataclass
class WordLookupResult:
    """Result of a dictionary lookup."""
    word: str
    status: WordStatus
    part_of_speech: Optional[str] = None
    definition: Optional[str] = None
    etymology: Optional[str] = None
    pronunciation: Optional[str] = None
    source: str = "unknown"
    raw_response: Optional[dict] = None
    error_message: Optional[str] = None


def _first_matching_entry(data: list, matches) -> Optional[dict]:
    """
    Find the entry that is actually about the word we asked for.

    These APIs return a *list* of entries and the exact match is not reliably
    first. Merriam-Webster in particular returns anything whose stems contain
    the query, so a lookup can come back headed by a related word. Reading only
    `data[0]` therefore reports NOT_FOUND for words the dictionary genuinely
    holds — which is the wrong answer in the more damaging direction, because
    the pipeline treats "not found" as "not a word".

    Scanning for the match cannot make a word wrongly valid: the predicates
    below still demand an exact match on the headword or its stems.
    """
    for entry in data:
        if isinstance(entry, dict) and matches(entry):
            return entry
    return None


class MerriamWebsterAPI:
    """
    Wrapper for Merriam-Webster Collegiate Dictionary API.
    
    Features:
    - Proper noun detection via response parsing
    - Rate limiting
    - Automatic retries on failure
    """
    
    def __init__(self, api_key: str = MW_API_KEY, cache: Optional[ResponseCache] = None):
        self.api_key = api_key
        self.base_url = MW_BASE_URL
        self.request_delay = MW_REQUEST_DELAY
        self._last_request_time = 0
        self.cache = cache if cache is not None else ResponseCache("collegiate")

        if not self.api_key:
            logger.warning("MW_API_KEY not set. Merriam-Webster lookups will fail.")
    
    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
        self._last_request_time = asyncio.get_event_loop().time()
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def lookup_word(self, word: str) -> WordLookupResult:
        """
        Look up a word in Merriam-Webster dictionary.
        
        Args:
            word: The word to look up (should be lowercase)
            
        Returns:
            WordLookupResult with status and metadata
        """
        if not self.api_key:
            return WordLookupResult(
                word=word,
                status=WordStatus.ERROR,
                error_message="API key not configured"
            )
        
        cached = self.cache.get(word)
        if cached is not None:
            return self._parse_response(word, cached)

        await self._rate_limit()

        url = f"{self.base_url}/{word}"
        params = {"key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                self.cache.put(word, data, response.status_code)
                return self._parse_response(word, data)

        except httpx.HTTPStatusError as e:
            # Deliberately not cached. A 429 is a statement about our quota, not
            # about the word, and caching it would bake a quota failure into the
            # record as though the dictionary had answered.
            logger.error(f"HTTP error for '{word}': {e}")
            return WordLookupResult(
                word=word,
                status=WordStatus.ERROR,
                error_message=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error for '{word}': {e}")
            return WordLookupResult(
                word=word,
                status=WordStatus.ERROR,
                error_message=str(e)
            )
    
    def _parse_response(self, word: str, data: list) -> WordLookupResult:
        """
        Parse Merriam-Webster API response.
        
        The API returns:
        - List of dict entries for valid words
        - List of strings for spelling suggestions (word not found)
        - Empty list for no results
        
        IMPORTANT: We must verify the returned entry actually matches our query word,
        as MW sometimes returns related words instead of the exact word.
        """
        # No results
        if not data:
            return WordLookupResult(
                word=word,
                status=WordStatus.NOT_FOUND,
                source="merriam-webster"
            )
        
        # Spelling suggestions (list of strings) = word not found
        if isinstance(data[0], str):
            return WordLookupResult(
                word=word,
                status=WordStatus.NOT_FOUND,
                source="merriam-webster"
            )
        
        # Valid dictionary entry - but verify it matches our word. Scan every
        # entry, not just the first: MW orders them by its own relevance, not by
        # exactness, so the match can sit behind a related headword.
        entry = _first_matching_entry(data, lambda e: self._entry_matches_word(e, word))

        if entry is None:
            return WordLookupResult(
                word=word,
                status=WordStatus.NOT_FOUND,
                source="merriam-webster"
            )

        # Check if it's an abbreviation or acronym
        if self._is_abbreviation(entry):
            return WordLookupResult(
                word=word,
                status=WordStatus.ABBREVIATION,
                source="merriam-webster",
                raw_response=entry
            )
        
        # Check if it's a proper noun
        if self._is_proper_noun(entry):
            return WordLookupResult(
                word=word,
                status=WordStatus.PROPER_NOUN,
                source="merriam-webster",
                raw_response=entry
            )
        
        # Extract metadata
        return WordLookupResult(
            word=word,
            status=WordStatus.VALID,
            part_of_speech=entry.get("fl"),  # "functional label" = part of speech
            definition=self._extract_definition(entry),
            etymology=self._extract_etymology(entry),
            pronunciation=self._extract_pronunciation(entry),
            source="merriam-webster",
            raw_response=entry
        )
    
    def _entry_matches_word(self, entry: dict, word: str) -> bool:
        """
        Verify that the dictionary entry actually matches our query word.
        
        MW API sometimes returns related words (e.g., query "noher" returns "mind"
        because "came into her mind" is in stems). We need exact matches.
        """
        word_lower = word.lower()
        
        # Check the meta.id field - this is the headword
        meta = entry.get("meta", {})
        entry_id = meta.get("id", "")
        
        # The ID format is "word:number" for homographs (e.g., "mind:1")
        base_id = entry_id.split(":")[0].lower() if entry_id else ""
        
        # Check for exact match
        if base_id == word_lower:
            return True
        
        # Check the headword from hwi
        hwi = entry.get("hwi", {})
        hw = hwi.get("hw", "")
        # Remove syllable markers (*) and compare
        clean_hw = hw.replace("*", "").lower()
        if clean_hw == word_lower:
            return True
        
        # Check stems - but only exact matches in the stems list
        stems = meta.get("stems", [])
        for stem in stems:
            if stem.lower() == word_lower:
                return True
        
        # No match found
        return False
    
    def _is_abbreviation(self, entry: dict) -> bool:
        """
        Detect if an entry is an abbreviation or acronym.
        
        Indicators:
        - Functional label (fl) contains "abbreviation"
        - Headword is all uppercase (e.g., "NASA", "FYI", "ASAP")
        """
        # Check functional label for "abbreviation"
        fl = entry.get("fl", "").lower()
        if "abbreviation" in fl:
            return True
        
        # Check if headword is all uppercase (typical for acronyms)
        hwi = entry.get("hwi", {})
        hw = hwi.get("hw", "")
        clean_hw = hw.replace("*", "")
        if clean_hw and len(clean_hw) > 1 and clean_hw.isupper():
            return True
        
        return False
    
    def _is_proper_noun(self, entry: dict) -> bool:
        """
        Detect if an entry is a proper noun.
        
        Indicators:
        - Headword is capitalized (but not all caps - that's an acronym)
        - Section is "biog" (biographical) or "geog" (geographical)
        """
        # Check headword capitalization
        hwi = entry.get("hwi", {})
        hw = hwi.get("hw", "")
        # Remove syllable markers and check first letter
        clean_hw = hw.replace("*", "")
        
        # All uppercase = acronym, not proper noun (handled separately)
        if clean_hw and clean_hw.isupper():
            return False
        
        # First letter uppercase = proper noun
        if clean_hw and clean_hw[0].isupper():
            return True
        
        # Check section type
        meta = entry.get("meta", {})
        section = meta.get("section", "")
        if section in ("biog", "geog"):
            return True
        
        return False
    
    def _extract_definition(self, entry: dict) -> Optional[str]:
        """Extract the first definition from an entry."""
        try:
            defs = entry.get("def", [])
            if defs:
                sseq = defs[0].get("sseq", [])
                if sseq:
                    sense = sseq[0][0]
                    if isinstance(sense, list) and len(sense) > 1:
                        dt = sense[1].get("dt", [])
                        if dt:
                            for item in dt:
                                if item[0] == "text":
                                    # Clean up definition text
                                    text = item[1]
                                    # Remove formatting codes
                                    text = text.replace("{bc}", "")
                                    text = text.replace("{sx|", "")
                                    text = text.replace("||}", "")
                                    return text.strip()
        except (IndexError, KeyError, TypeError):
            pass
        return None
    
    def _extract_etymology(self, entry: dict) -> Optional[str]:
        """Extract etymology from an entry."""
        try:
            et = entry.get("et", [])
            if et:
                for item in et:
                    if item[0] == "text":
                        return item[1]
        except (IndexError, KeyError, TypeError):
            pass
        return None
    
    def _extract_pronunciation(self, entry: dict) -> Optional[str]:
        """Extract pronunciation from an entry."""
        try:
            hwi = entry.get("hwi", {})
            prs = hwi.get("prs", [])
            if prs:
                return prs[0].get("mw")  # Merriam-Webster phonetic
        except (IndexError, KeyError, TypeError):
            pass
        return None


class FreeDictionaryAPI:
    """
    Wrapper for Free Dictionary API (fallback).
    
    Unlimited requests, no API key needed.
    Less authoritative than Merriam-Webster.
    """
    
    def __init__(self, cache: Optional[ResponseCache] = None):
        self.base_url = FREE_DICT_BASE_URL
        self.cache = cache if cache is not None else ResponseCache("free")

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def lookup_word(self, word: str) -> WordLookupResult:
        """Look up a word in Free Dictionary API."""
        cached = self.cache.get(word)
        if cached is not None:
            return self._parse_response(word, cached)

        url = f"{self.base_url}/{word}"

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(url)

                if response.status_code == 404:
                    # A 404 here is the dictionary answering "no such word",
                    # so it is worth caching — unlike a quota or network failure.
                    self.cache.put(word, [], 404)
                    return WordLookupResult(
                        word=word,
                        status=WordStatus.NOT_FOUND,
                        source="free-dictionary"
                    )

                response.raise_for_status()
                data = response.json()

                self.cache.put(word, data, response.status_code)
                return self._parse_response(word, data)

        except Exception as e:
            logger.error(f"Free Dictionary error for '{word}': {e}")
            return WordLookupResult(
                word=word,
                status=WordStatus.ERROR,
                error_message=str(e)
            )
    
    def _parse_response(self, word: str, data: list) -> WordLookupResult:
        """Parse Free Dictionary API response."""
        if not data:
            return WordLookupResult(
                word=word,
                status=WordStatus.NOT_FOUND,
                source="free-dictionary"
            )
        
        # An entry with no `word` field at all was accepted before this scan
        # existed, and still is — the change here is only that a later entry can
        # now supply the match, never that a previously-accepted one is refused.
        def _matches(e: dict) -> bool:
            entry_word = e.get("word", "").lower()
            return not entry_word or entry_word == word.lower()

        entry = _first_matching_entry(data, _matches)

        if entry is None:
            return WordLookupResult(
                word=word,
                status=WordStatus.NOT_FOUND,
                source="free-dictionary"
            )
        
        # Extract part of speech from first meaning
        part_of_speech = None
        definition = None
        meanings = entry.get("meanings", [])
        if meanings:
            part_of_speech = meanings[0].get("partOfSpeech")
            defs = meanings[0].get("definitions", [])
            if defs:
                definition = defs[0].get("definition")
        
        return WordLookupResult(
            word=word,
            status=WordStatus.VALID,
            part_of_speech=part_of_speech,
            definition=definition,
            pronunciation=entry.get("phonetic"),
            source="free-dictionary",
            raw_response=entry
        )


class MerriamWebsterMedicalAPI:
    """
    Wrapper for Merriam-Webster Medical Dictionary API.
    
    Provides access to specialized medical terminology not in Collegiate.
    """
    
    def __init__(self, api_key: str = None, cache: Optional[ResponseCache] = None):
        self.api_key = api_key or MW_MEDICAL_API_KEY
        self.base_url = MW_MEDICAL_BASE_URL
        self.request_delay = MW_REQUEST_DELAY
        self._last_request_time = 0
        self.cache = cache if cache is not None else ResponseCache("medical")

        if not self.api_key:
            logger.debug("MW_MEDICAL_API_KEY not set. Medical lookups will be skipped.")
    
    @property
    def is_configured(self) -> bool:
        """Check if the Medical API is configured."""
        return bool(self.api_key)
    
    async def _rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self.request_delay:
            await asyncio.sleep(self.request_delay - time_since_last)
        self._last_request_time = asyncio.get_event_loop().time()
    
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def lookup_word(self, word: str) -> WordLookupResult:
        """Look up a word in Merriam-Webster Medical dictionary."""
        if not self.api_key:
            return WordLookupResult(
                word=word,
                status=WordStatus.NOT_FOUND,
                error_message="Medical API key not configured"
            )
        
        cached = self.cache.get(word)
        if cached is not None:
            return self._parse_response(word, cached)

        await self._rate_limit()

        url = f"{self.base_url}/{word}"
        params = {"key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                self.cache.put(word, data, response.status_code)
                return self._parse_response(word, data)

        except httpx.HTTPStatusError as e:
            logger.error(f"Medical API HTTP error for '{word}': {e}")
            return WordLookupResult(
                word=word,
                status=WordStatus.ERROR,
                error_message=str(e)
            )
        except Exception as e:
            logger.error(f"Medical API error for '{word}': {e}")
            return WordLookupResult(
                word=word,
                status=WordStatus.ERROR,
                error_message=str(e)
            )
    
    def _parse_response(self, word: str, data: list) -> WordLookupResult:
        """Parse Medical Dictionary API response."""
        if not data:
            return WordLookupResult(
                word=word,
                status=WordStatus.NOT_FOUND,
                source="merriam-webster-medical"
            )
        
        if isinstance(data[0], str):
            return WordLookupResult(
                word=word,
                status=WordStatus.NOT_FOUND,
                source="merriam-webster-medical"
            )
        
        entry = _first_matching_entry(data, lambda e: self._entry_matches_word(e, word))

        if entry is None:
            return WordLookupResult(
                word=word,
                status=WordStatus.NOT_FOUND,
                source="merriam-webster-medical"
            )
        
        # Extract metadata
        return WordLookupResult(
            word=word,
            status=WordStatus.VALID,
            part_of_speech=entry.get("fl"),
            definition=self._extract_definition(entry),
            source="merriam-webster-medical",
            raw_response=entry
        )
    
    def _entry_matches_word(self, entry: dict, word: str) -> bool:
        """
        Verify that the dictionary entry actually matches our query word.
        Same logic as Collegiate API.
        """
        word_lower = word.lower()
        
        # Check the meta.id field
        meta = entry.get("meta", {})
        entry_id = meta.get("id", "")
        base_id = entry_id.split(":")[0].lower() if entry_id else ""
        
        if base_id == word_lower:
            return True
        
        # Check the headword from hwi
        hwi = entry.get("hwi", {})
        hw = hwi.get("hw", "")
        clean_hw = hw.replace("*", "").lower()
        if clean_hw == word_lower:
            return True
        
        # Check stems
        stems = meta.get("stems", [])
        for stem in stems:
            if stem.lower() == word_lower:
                return True
        
        return False
    
    def _extract_definition(self, entry: dict) -> Optional[str]:
        """Extract the first definition from an entry."""
        try:
            defs = entry.get("def", [])
            if defs:
                sseq = defs[0].get("sseq", [])
                if sseq:
                    sense = sseq[0][0]
                    if isinstance(sense, list) and len(sense) > 1:
                        dt = sense[1].get("dt", [])
                        if dt:
                            for item in dt:
                                if item[0] == "text":
                                    text = item[1]
                                    text = text.replace("{bc}", "")
                                    return text.strip()
        except (IndexError, KeyError, TypeError):
            pass
        return None


class DictionaryAPIClient:
    """
    Unified dictionary API client.
    
    Uses Merriam-Webster Collegiate as primary, Medical as secondary,
    Free Dictionary as fallback.
    """
    
    #: The order the daily pipeline has always used. Changing this changes what
    #: gets promoted every night, so it is a default, not a suggestion.
    DEFAULT_ORDER = ("collegiate", "medical", "free")

    def __init__(self, use_medical: bool = True):
        self.mw = MerriamWebsterAPI()
        self.mw_medical = MerriamWebsterMedicalAPI() if use_medical else None
        self.free_dict = FreeDictionaryAPI()

    async def lookup_word(
        self,
        word: str,
        use_fallback: bool = True,
        use_medical: bool = True
    ) -> WordLookupResult:
        """
        Look up a word using available APIs.

        Args:
            word: The word to look up
            use_fallback: If True, try Free Dictionary if MW fails
            use_medical: If True, try Medical Dictionary if Collegiate fails

        Returns:
            WordLookupResult
        """
        # Try Merriam-Webster Collegiate first
        result = await self.mw.lookup_word(word)

        # Try Medical Dictionary if Collegiate didn't find it
        if use_medical and result.status == WordStatus.NOT_FOUND:
            if self.mw_medical and self.mw_medical.is_configured:
                logger.debug(f"Collegiate didn't find '{word}', trying Medical")
                medical_result = await self.mw_medical.lookup_word(word)
                if medical_result.status == WordStatus.VALID:
                    return medical_result

        # Use Free Dictionary fallback if still not found
        if use_fallback and result.status == WordStatus.NOT_FOUND:
            logger.debug(f"MW didn't find '{word}', trying Free Dictionary")
            result = await self.free_dict.lookup_word(word)

        return result

    async def lookup_all(
        self,
        word: str,
        order: tuple = DEFAULT_ORDER,
    ) -> dict:
        """
        Consult sources in `order`, stopping at the first that rules on the word,
        and report what every source consulted actually said.

        This exists for measurement rather than for promotion. `lookup_word`
        above answers "should this be promoted"; this answers "what does each
        dictionary say, and which ones were even asked". Two differences matter:

        * A source that **errors** is not a source that said no. `lookup_word`
          only falls through on NOT_FOUND, so a rate-limited Collegiate ends the
          search; here it falls through and is recorded as an error, because a
          quota failure must never be read as a verdict about the word.
        * ABBREVIATION and PROPER_NOUN are rulings, not misses. They stop the
          search — the dictionary has answered.

        Returns a dict of `statuses` per source, plus the deciding source and its
        WordLookupResult (None when nothing ruled).
        """
        sources = {
            "collegiate": self.mw,
            "medical": self.mw_medical,
            "free": self.free_dict,
        }
        decided_by = {WordStatus.VALID, WordStatus.ABBREVIATION, WordStatus.PROPER_NOUN}

        statuses: dict = {}
        deciding_source = None
        deciding_result = None

        for name in order:
            api = sources.get(name)
            if api is None:
                statuses[name] = "unconfigured"
                continue
            if name == "medical" and not api.is_configured:
                statuses[name] = "unconfigured"
                continue

            result = await api.lookup_word(word)
            statuses[name] = result.status.value

            if result.status in decided_by:
                deciding_source = name
                deciding_result = result
                break

        return {
            "word": word,
            "statuses": statuses,
            "deciding_source": deciding_source,
            "result": deciding_result,
        }
    
    async def batch_lookup(
        self, 
        words: list[str],
        use_fallback: bool = True,
        max_concurrent: int = 10
    ) -> list[WordLookupResult]:
        """
        Look up multiple words concurrently.
        
        Args:
            words: List of words to look up
            use_fallback: If True, try fallback API
            max_concurrent: Maximum concurrent requests
            
        Returns:
            List of WordLookupResult
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def limited_lookup(word: str) -> WordLookupResult:
            async with semaphore:
                return await self.lookup_word(word, use_fallback)
        
        tasks = [limited_lookup(word) for word in words]
        return await asyncio.gather(*tasks)


# Convenience function for synchronous usage
def lookup_word_sync(word: str) -> WordLookupResult:
    """Synchronous wrapper for word lookup."""
    client = DictionaryAPIClient()
    return asyncio.run(client.lookup_word(word))


if __name__ == "__main__":
    # Test the API
    import asyncio
    
    async def test():
        client = DictionaryAPIClient()
        
        test_words = ["hello", "boba", "asdfghjkl", "Paris", "google"]
        
        for word in test_words:
            result = await client.lookup_word(word)
            print(f"\n{word}:")
            print(f"  Status: {result.status.value}")
            print(f"  Part of Speech: {result.part_of_speech}")
            print(f"  Definition: {result.definition[:50] if result.definition else None}...")
            print(f"  Source: {result.source}")
    
    asyncio.run(test())
