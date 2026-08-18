"""
The four negative-control families — §6.3 — built deterministically.

Every family is selected by sha256 ranking (the project's determinism rule):
same code, same inputs, same families, on any machine. Sizes are recorded in
the gate report; nothing here is sampled by a library RNG.

  ocr       real held-out positives corrupted through the D-012 confusion
            pairs, source->artifact, one site per word chosen by hash unit.
            Kept only if the corruption is NOT itself in the reference lexicon.
            This family is SR3's instrument.
  pseudo    drawn from the trained character model itself — hard negatives by
            construction — kept only if absent from EVERY ingested source's
            key set (verified against the derived sets, not assumed).
  foreign   lowercase Wiktionary titles with NO English section and no hit on
            any binary detector: real spellings of real words, none of them
            English. The `agiler` failure mode, industrialised.
  mw        the 441 inflections Merriam-Webster explicitly declined when asked
            about their stems (ledgers stage 3 and 4, outcome =
            inflection-absent) — real, already-adjudicated negatives.
"""

from __future__ import annotations

import csv
import hashlib
import itertools

from research.ingest.common import REPO, read_derived
from . import ocr
from .partitions import hash_unit

FAMILY_SIZE = 2000


def _rank(words, seed):
    return sorted(words, key=lambda w: hashlib.sha256(f"{seed}:{w}".encode()).hexdigest())


def ocr_family(test_positives, reference) -> list[str]:
    out = []
    seen = set()
    for w in _rank(test_positives, "ocr-family"):
        c = ocr.corrupt(w, hash_unit(w, "ocr-site"))
        if c and c not in reference and c not in seen and c != w:
            seen.add(c)
            out.append(c)
        if len(out) >= FAMILY_SIZE:
            break
    return out


def pseudo_family(model, all_source_keys) -> list[str]:
    def units(tag):
        for i in itertools.count():
            h = hashlib.sha256(f"pseudo:{tag}:{i}".encode()).digest()
            yield int.from_bytes(h[:8], "big") / 2**64
    out, seen = [], set()
    for tag in itertools.count():
        w = model.sample_word(units(tag))
        if 2 <= len(w) <= 24 and w not in all_source_keys and w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= FAMILY_SIZE:
            break
    return out


def foreign_family(detector_hit_words) -> list[str]:
    titles = read_derived("wiktionary_titles")
    english = read_derived("wiktionary_english")
    pool = titles - english - detector_hit_words
    return _rank(pool, "foreign-family")[:FAMILY_SIZE]


def mw_family() -> list[str]:
    forms = set()
    for name in ("ledger_stage3.csv", "ledger_stage4.csv"):
        with open(REPO / "corrections" / name, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("outcome") == "inflection-absent":
                    forms.update(row.get("forms_missing", "").split())
    return sorted(forms)
