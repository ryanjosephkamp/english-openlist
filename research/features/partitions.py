"""
Leakage-clean partitions for the character model — PROTOCOL §3.3.

The training pool is the STRONG POSITIVES: frame words fired by at least
MIN_DETECTORS of the twelve binary detectors (the eleven detector columns plus
SCOWL-presence). Broad agreement across near-independent lineages is the
closest thing this programme has to labels it did not invent.

The pool splits train / dev / test by sha256(f"{SEED}:{word}") ranking — the
project's determinism rule. No library RNG, recomputable in any language,
immune to stdlib changes. The split is BY HASH RANGE, not by sorted position,
so membership of one word never depends on which other words are in the pool.

Two leakage guarantees downstream code must honour, both recorded in the
features manifest:

  * The held-out perplexity gate and every negative-control separation use the
    TEST partition (or sets disjoint from the pool entirely). Nothing the
    model trained on is ever evaluated.
  * The Phase 4 calibration sample must exclude TRAIN ∪ DEV. The manifest
    carries the seed and rule so Phase 4 can re-derive the exclusion set
    exactly.
"""

from __future__ import annotations

import hashlib

SEED = "phase2-partitions-2026-08-17"
MIN_DETECTORS = 8

#: hash-range boundaries: [0, TRAIN_END) train, [TRAIN_END, DEV_END) dev, rest test
TRAIN_END = 0.70
DEV_END = 0.80

DETECTOR_COLUMNS = [
    "wordnet", "wiktionary_english", "web2",
    "hunspell_en_US", "hunspell_en_GB", "hunspell_en_CA", "hunspell_en_AU",
    "enable1", "sowpods_legacy", "nwl2023", "csw21",
]  # + scowl_tier > 0 counted by the caller


def hash_unit(word: str, seed: str = SEED) -> float:
    """sha256(seed:word) mapped to [0, 1). The whole determinism story."""
    h = hashlib.sha256(f"{seed}:{word}".encode()).digest()
    return int.from_bytes(h[:8], "big") / 2**64


def assign(word: str) -> str:
    u = hash_unit(word)
    if u < TRAIN_END:
        return "train"
    if u < DEV_END:
        return "dev"
    return "test"
