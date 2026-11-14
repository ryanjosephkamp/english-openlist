"""
What a published record holds.

`merged_valid_dict.json` is published with every nightly run. Each record is
reduced to the same few fields before it is uploaded, so a record says what the
word is and which open sources list it, and nothing about the list's private
build history:

- `word` and `length`;
- `attested_by`: the openly licensed sources whose own files list the word
  (`scripts/open_attestation.py`). Words the nightly run adds carry none until
  the next attestation pass;
- `source` and `added_date`, only when `source` is one of `PUBLISHED_SOURCES`:
  the synthetic engine, the domain extracts, the Free Dictionary API, and the
  nightly run's promotions. Any other value is dropped with its date.

Everything else goes: the discovery log, the verification pipeline's working
fields, and any text a dictionary API returned. The projection is idempotent,
so it runs on every upload, and a field or a `source` value nobody has decided
to publish can't reach the dataset: it is dropped, and the counts say so.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import orjson

from scripts.open_attestation import ATTESTING_KEYS

logger = logging.getLogger(__name__)

#: `source` values a published record may carry.
PUBLISHED_SOURCES = (
    "synthetic_generation",
    "authoritative_extracts",
    "extended_domain_sources",
    "free-dictionary",
    "invalid_list_recovery",
)

#: The fields of a published record, in this order.
PUBLISHED_FIELDS = ("word", "length", "attested_by", "source", "added_date")

#: Where a record may keep the date it was added, in order of preference.
DATE_FIELDS = ("added_date", "created_date", "validation_date")


@dataclass
class Counts:
    records: int = 0
    reshaped: int = 0
    sources_dropped: int = 0
    fields_dropped: int = 0
    by_field: dict = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return self.reshaped > 0

    def summary(self) -> str:
        return (f"{self.reshaped} records reshaped, {self.sources_dropped} unpublished "
                f"source values dropped, {self.fields_dropped} fields dropped, over "
                f"{self.records} records")


def _day(value: object) -> Optional[str]:
    if not isinstance(value, str) or len(value) < 10:
        return None
    day = value[:10]
    if day[4] == "-" and day[7] == "-" and day.replace("-", "").isdigit():
        return day
    return None


def project_record(word: str, record: dict, counts: Optional[Counts] = None) -> dict:
    """The published form of a record: a new dict holding only `PUBLISHED_FIELDS`."""
    counts = counts if counts is not None else Counts()
    out: dict = {"word": word, "length": len(word)}

    attested = record.get("attested_by")
    if isinstance(attested, list):
        out["attested_by"] = [key for key in ATTESTING_KEYS if key in attested]

    source = record.get("source")
    if source in PUBLISHED_SOURCES:
        out["source"] = source
        for name in DATE_FIELDS:
            day = _day(record.get(name))
            if day:
                out["added_date"] = day
                break
    elif source is not None:
        counts.sources_dropped += 1

    for name in record:
        if name not in out:
            counts.fields_dropped += 1
            counts.by_field[name] = counts.by_field.get(name, 0) + 1
    if out != record:
        counts.reshaped += 1
    return out


def project_dictionary(valid_dict: dict) -> tuple[dict, Counts]:
    """Every record in its published form, sorted by word.

    Sorted rather than kept in the order the records were written: that order
    groups words by the batch that wrote them, which is build history too.
    """
    counts = Counts()
    published = {}
    for word in sorted(valid_dict):
        record = valid_dict[word]
        counts.records += 1
        published[word] = project_record(word, record if isinstance(record, dict) else {}, counts)
    if list(published) != list(valid_dict):
        counts.reshaped += 1
    return published, counts


def clean_file(path: Path) -> Counts:
    """Reduce a `merged_valid_dict.json` to its published form; write it only if something changed."""
    valid_dict = orjson.loads(path.read_bytes())
    published, counts = project_dictionary(valid_dict)
    if counts.changed:
        path.write_bytes(orjson.dumps(published, option=orjson.OPT_INDENT_2))
        logger.info("Cleaned %s: %s", path, counts.summary())
    else:
        logger.info("Nothing to clean in %s (%d records)", path, counts.records)
    return counts
