"""
Wiktionary as a second source.

Merriam-Webster could not adjudicate this dataset. It has no entry for 95.8% of
the words one LLM flagged, and covers 9.2% of the stems behind the synthetic
plurals. That is a coverage limit rather than a budget one: MW does not carry
taxonomic, chemical or obscure technical vocabulary, and it does not give
inflected forms their own headwords. No amount of quota fixes either.

Wiktionary does both. It gives `abidings` its own page, which is exactly the
question this project keeps needing to ask.

**Two files, and the cheap one does most of the work.** The full English extract
is 3 GB. The list of every page title is 27 MB and downloads in five seconds,
and because Wiktionary pages inflected forms separately, a title's existence
already answers "is this a form Wiktionary recognises". That is the screen.

**The catch, and why the screen is not the answer.** Wiktionary puts every
language on one page. `agiler` has a page because it is German. So a title hit
means *some* language uses that spelling, and English has to be confirmed
separately — which is what `has_english_section` is for, over the API, and only
for the words that hit.

**A hit rescues; a miss does not condemn.** Wiktionary is community-edited, so
its presence is weaker evidence than Merriam-Webster's and its absence is much
weaker still. This module is used to find words that should not have been
demoted, not to demote more.
"""

import gzip
import logging
import re
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import PHASE3_ROOT

logger = logging.getLogger(__name__)

CACHE_DIR = PHASE3_ROOT / ".cache" / "wiktionary"
TITLES_FILE = CACHE_DIR / "all-titles.gz"
TITLES_URL = ("https://dumps.wikimedia.org/enwiktionary/latest/"
              "enwiktionary-latest-all-titles-in-ns0.gz")

API = "https://en.wiktionary.org/w/api.php"

#: Wikimedia asks for a descriptive User-Agent that identifies the operator, and
#: rate-limits anonymous clients that do not send one.
USER_AGENT = ("english-openlist/1.0 (https://github.com/ryanjosephkamp/english-openlist; "
              "dataset validation)")

#: The API accepts 50 titles per query for anonymous callers.
BATCH = 50

ENGLISH_HEADING = re.compile(r"^==\s*English\s*==\s*$", re.MULTILINE)


def download_titles(force: bool = False) -> Path:
    """Fetch the title index if it is not already here. 27 MB."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if TITLES_FILE.exists() and not force:
        logger.info("Titles already present: %s", TITLES_FILE)
        return TITLES_FILE

    logger.info("Downloading %s", TITLES_URL)
    with httpx.stream("GET", TITLES_URL, follow_redirects=True, timeout=300) as r:
        r.raise_for_status()
        with open(TITLES_FILE, "wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
    logger.info("Wrote %s (%.1f MB)", TITLES_FILE, TITLES_FILE.stat().st_size / 1e6)
    return TITLES_FILE


def load_titles() -> set[str]:
    """Every page title in the main namespace, about nine million of them."""
    download_titles()
    titles = set()
    with gzip.open(TITLES_FILE, "rt", encoding="utf-8") as f:
        next(f)  # header: page_title
        for line in f:
            titles.add(line.rstrip("\n"))
    logger.info("Loaded %d Wiktionary titles", len(titles))
    return titles


def has_english_section(words: list[str], delay: float = 0.2) -> dict[str, bool]:
    """
    Which of these pages actually carry an English entry.

    Fetches the wikitext and looks for an `== English ==` heading, which is how
    Wiktionary separates languages on a shared page. Batched 50 at a time, so a
    couple of thousand words costs tens of requests rather than thousands.

    A word missing from the response entirely (no such page) comes back False.
    """
    result: dict[str, bool] = {w: False for w in words}
    headers = {"User-Agent": USER_AGENT}

    with httpx.Client(timeout=60, headers=headers, follow_redirects=True) as client:
        for i in range(0, len(words), BATCH):
            batch = words[i:i + BATCH]
            params = {
                "action": "query",
                "format": "json",
                "formatversion": "2",
                "prop": "revisions",
                "rvprop": "content",
                "rvslots": "main",
                "titles": "|".join(batch),
            }
            try:
                r = client.get(API, params=params)
                r.raise_for_status()
                pages = r.json().get("query", {}).get("pages", [])
            except Exception as exc:
                # Never silently record "no English" for a request that failed;
                # that would read as evidence against the word.
                logger.error("batch %d failed: %s", i // BATCH, exc)
                for w in batch:
                    result.pop(w, None)
                continue

            for page in pages:
                title = page.get("title")
                if page.get("missing"):
                    continue
                revs = page.get("revisions") or []
                if not revs:
                    continue
                text = (revs[0].get("slots", {}).get("main", {}) or {}).get("content", "")
                if title in result:
                    result[title] = bool(ENGLISH_HEADING.search(text))

            if i % (BATCH * 10) == 0:
                logger.info("  %d/%d checked", min(i + BATCH, len(words)), len(words))
            time.sleep(delay)

    return result
