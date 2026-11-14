"""
Which openly licensed sources list each word.

Every record of the published dictionary carries `attested_by`: the keys of the
sources below whose own files list the word, in the order of `SOURCES`. A word
counts as listed when the source's file holds exactly that string, lowercase.
For WordNet, a word also counts when WordNet's own morphology (`morphy`, with
its exception lists) maps it to a lemma, so `abacuses` counts through `abacus`.

The pass runs on a local machine against pinned copies of the sources, not in
the nightly run: they come to about 60 MB, and they change only when a source
releases. Words the nightly run adds afterward carry no `attested_by` until the
next pass. NOTICES.md carries each source's notice and license.

Usage:

    python scripts/open_attestation.py --sources DIR --dict merged_valid_dict.json

`DIR` holds 1 plain file per source, named `<key>.txt`, 1 word per line. The
`--write` flag adds `attested_by` to the dictionary in place; without it the
script prints the counts only.
"""

from __future__ import annotations

import argparse
import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

import orjson

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Source:
    name: str
    version: str
    license: str
    url: str


#: The attesting sources, in the order `attested_by` lists them.
SOURCES: dict[str, Source] = {
    "wiktionary": Source(
        name="The English Wiktionary",
        version="pages-articles dump of August 1, 2026: page titles with an English section",
        license="CC BY-SA 4.0 and GFDL",
        url="https://dumps.wikimedia.org/enwiktionary/",
    ),
    "wordnet": Source(
        name="WordNet 3.0 (Princeton University)",
        version="3.0, as nltk distributes it: lemmas, and forms its morphy maps to a lemma",
        license="WordNet 3.0 license",
        url="https://wordnet.princeton.edu/",
    ),
    "scowl": Source(
        name="SCOWL (Kevin Atkinson)",
        version="2020.12.07, all sizes and spelling varieties",
        license="SCOWL's permissive notice",
        url="http://wordlist.aspell.net/",
    ),
    "libreoffice": Source(
        name="The LibreOffice English dictionaries",
        version="en_US, en_GB, en_CA, and en_AU at commit f2ff9905, every form the affix rules produce",
        license="SCOWL's notice (en_US, en_CA, en_AU); LGPL (en_GB)",
        url="https://github.com/LibreOffice/dictionaries/tree/master/en",
    ),
    "enable": Source(
        name="ENABLE (Alan Beale and M. Cooper)",
        version="enable1.txt, 172,823 words",
        license="Public domain",
        url="https://github.com/dolph/dictionary",
    ),
    "wordfreq": Source(
        name="wordfreq (Robyn Speer)",
        version="3.1.1, English: every word it gives a frequency",
        license="CC BY-SA 4.0 (data)",
        url="https://github.com/rspeer/wordfreq",
    ),
}

ATTESTING_KEYS = tuple(SOURCES)


def read_list(path: Path) -> set[str]:
    """A plain word list: 1 word per line, compared lowercase."""
    with path.open(encoding="utf-8") as handle:
        return {line.strip().lower() for line in handle if line.strip()}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def wordnet_morphy() -> Optional[Callable[[str], bool]]:
    """WordNet's morphology through nltk, or None when nltk or its WordNet is missing."""
    try:
        from nltk.corpus import wordnet
        wordnet.ensure_loaded()
    except Exception:  # noqa: BLE001 - nltk raises LookupError or ImportError
        return None

    def maps_to_lemma(word: str) -> bool:
        for pos in ("n", "v", "a", "r"):
            if wordnet.morphy(word, pos):
                return True
        return False

    return maps_to_lemma


class Attester:
    """Answers which sources list a word, from the plain lists in a directory."""

    def __init__(self, lists: dict[str, set[str]], morphy: Optional[Callable[[str], bool]] = None):
        unknown = set(lists) - set(SOURCES)
        if unknown:
            raise ValueError(f"not an attesting source: {', '.join(sorted(unknown))}")
        self.lists = lists
        self.morphy = morphy

    @classmethod
    def from_directory(cls, directory: Path, use_morphy: bool = True) -> "Attester":
        lists = {}
        for key in SOURCES:
            path = directory / f"{key}.txt"
            if not path.exists():
                raise FileNotFoundError(f"{path}: every attesting source needs its list")
            lists[key] = read_list(path)
            logger.info("%s: %d entries, sha256 %s", key, len(lists[key]), sha256_of(path))
        morphy = wordnet_morphy() if use_morphy else None
        if use_morphy and morphy is None:
            raise RuntimeError("WordNet's morphology needs nltk and its WordNet corpus")
        return cls(lists, morphy)

    def sources_of(self, word: str) -> list[str]:
        key = word.lower()
        found = []
        for name in SOURCES:
            listed = self.lists.get(name, set())
            if key in listed or (name == "wordnet" and self.morphy is not None and self.morphy(key)):
                found.append(name)
        return found

    def attest(self, words: Iterable[str]) -> dict[str, list[str]]:
        return {word: self.sources_of(word) for word in words}


def count(attested: dict[str, list[str]]) -> dict[str, int]:
    """Words per source, and words no source lists."""
    totals = {name: 0 for name in SOURCES}
    unlisted = 0
    for found in attested.values():
        for name in found:
            totals[name] += 1
        if not found:
            unlisted += 1
    totals["none"] = unlisted
    return totals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sources", type=Path, required=True, help="Directory of <key>.txt lists")
    parser.add_argument("--dict", type=Path, required=True, help="merged_valid_dict.json")
    parser.add_argument("--write", action="store_true", help="Add attested_by to every record in place")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    attester = Attester.from_directory(args.sources)
    valid_dict = orjson.loads(args.dict.read_bytes())
    attested = attester.attest(valid_dict)
    for name, total in count(attested).items():
        print(f"{name:12s} {total:>9,}")
    if args.write:
        for word, record in valid_dict.items():
            if isinstance(record, dict):
                record["attested_by"] = attested[word]
        args.dict.write_bytes(orjson.dumps(valid_dict, option=orjson.OPT_INDENT_2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
