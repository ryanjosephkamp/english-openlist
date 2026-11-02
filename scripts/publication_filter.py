"""
What the published records leave out.

`merged_valid_dict.json` is published with every nightly run. Its records
carry some labels and some dictionary text that a public file shouldn't:

- `source` names the intake a record was written by. Two of its values name a
  source whose terms don't allow publishing the label: the tournament word list
  (`twl_scrabble_dictionary`) and the Merriam-Webster dictionaries
  (`merriam-webster`, `merriam-webster-medical`). They become `withheld_intake`
  and `withheld_dictionary`, so a record still says that its intake was
  withheld, and the site's counts by intake don't move.
- `candidate_source` is the discovery log, each entry suffixed `_valid` or
  `_unlikely`. The entries for the COCA frequency list, Collins, and the Linux
  and NLTK word lists are dropped.
- `definition`, `pronunciation`, `etymology`, and `raw_response` hold what a
  dictionary API returned for the 221 records that went through the promotion
  path. A verdict and the name of the source that gave it stay
  (`dictionary_verdict`, `source`); the API's own text goes.

The filter is idempotent, so it runs on every upload and a new label can't
reach the dataset unnoticed: an unknown `source` value passes, but the site's
build stops on one it doesn't know (`tools/eol-build/src/channels.ts`).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import orjson

logger = logging.getLogger(__name__)

#: `source` values that name a withheld source, and what replaces them.
SOURCE_REPLACEMENTS = {
    "twl_scrabble_dictionary": "withheld_intake",
    "merriam-webster": "withheld_dictionary",
    "merriam-webster-medical": "withheld_dictionary",
}

#: Discovery-log names that are dropped, with either suffix.
WITHHELD_DISCOVERY = ("coca_frequency", "collins", "linux", "nltk")

#: Fields that hold a dictionary API's own text.
DICTIONARY_TEXT_FIELDS = ("definition", "pronunciation", "etymology", "raw_response")


@dataclass
class Counts:
    records: int = 0
    sources: int = 0
    discovery_entries: int = 0
    text_fields: int = 0
    by_source: dict = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return bool(self.sources or self.discovery_entries or self.text_fields)

    def summary(self) -> str:
        return (f"{self.sources} source labels replaced, {self.discovery_entries} "
                f"discovery-log entries dropped, {self.text_fields} dictionary text "
                f"fields dropped, over {self.records} records")


def _withheld_discovery(entry: object) -> bool:
    if not isinstance(entry, str):
        return False
    for suffix in ("_valid", "_unlikely"):
        if entry.endswith(suffix):
            entry = entry[: -len(suffix)]
            break
    return entry in WITHHELD_DISCOVERY


def clean_record(record: dict, counts: Optional[Counts] = None) -> dict:
    """The record without what a public file leaves out; the same object, edited."""
    counts = counts if counts is not None else Counts()

    source = record.get("source")
    if source in SOURCE_REPLACEMENTS:
        record["source"] = SOURCE_REPLACEMENTS[source]
        counts.sources += 1
        counts.by_source[source] = counts.by_source.get(source, 0) + 1

    discovery = record.get("candidate_source")
    if isinstance(discovery, list):
        kept = [entry for entry in discovery if not _withheld_discovery(entry)]
        if len(kept) != len(discovery):
            counts.discovery_entries += len(discovery) - len(kept)
            record["candidate_source"] = kept

    for name in DICTIONARY_TEXT_FIELDS:
        if name in record:
            del record[name]
            counts.text_fields += 1

    return record


def clean_dictionary(valid_dict: dict) -> Counts:
    """Clean every record of a loaded dictionary in place."""
    counts = Counts()
    for record in valid_dict.values():
        if isinstance(record, dict):
            counts.records += 1
            clean_record(record, counts)
    return counts


def clean_file(path: Path) -> Counts:
    """Clean a `merged_valid_dict.json` in place; write it only if something changed."""
    valid_dict = orjson.loads(path.read_bytes())
    counts = clean_dictionary(valid_dict)
    if counts.changed:
        path.write_bytes(orjson.dumps(valid_dict, option=orjson.OPT_INDENT_2))
        logger.info("Cleaned %s: %s", path, counts.summary())
    else:
        logger.info("Nothing to clean in %s (%d records)", path, counts.records)
    return counts
