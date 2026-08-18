"""
Load the evidence matrix into the shapes the models eat.

Patterns: the 12 binary detectors collapse 9.79M rows into a few hundred
distinct patterns with counts — the representation everything in PROTOCOL §4
fits over. Per-word pattern ids are kept so posteriors map back to words.

Features (S4/S5): standardized continuous channels with missingness
indicators. NaN is data here — "Google Books never saw it" is informative —
so absence becomes an indicator column and the value is imputed to zero
AFTER standardization (i.e. to the mean), which keeps the linear predictor of
a missing channel neutral rather than extreme. Scaler parameters are saved so
the pilot's posteriors are reproducible from the saved fit alone.
"""

from __future__ import annotations

import json

import numpy as np
import pyarrow.parquet as pq

from research.ingest.common import REPO

DATA = REPO / "research" / "data"

DETECTORS = ["wordnet", "wiktionary_english", "web2",
             "hunspell_en_US", "hunspell_en_GB", "hunspell_en_CA",
             "hunspell_en_AU", "enable1", "sowpods_legacy", "nwl2023",
             "csw21"]          # + scowl_present appended below -> K = 12

#: The nine declared dependence edges (MANIFEST derives_from), by detector
#: index — resolved after scowl joins the list.
EDGE_NAMES = [("hunspell_en_US", "scowl"), ("hunspell_en_GB", "scowl"),
              ("hunspell_en_CA", "scowl"), ("hunspell_en_AU", "scowl"),
              ("hunspell_en_GB", "hunspell_en_US"),
              ("hunspell_en_CA", "hunspell_en_US"),
              ("hunspell_en_AU", "hunspell_en_US"),
              ("enable1", "nwl2023"), ("sowpods_legacy", "csw21")]

FEATURES = ["orthotactic_logp_per_char", "ocr_neighbor_freq_ratio",
            "gb_log10_volume", "gb_span_fill", "gb_tokens_per_volume",
            "zipf_resid", "morph_productivity_vn"]


def detector_names() -> list[str]:
    return DETECTORS + ["scowl"]


def edge_indices() -> list[tuple[int, int]]:
    names = detector_names()
    return [(names.index(a), names.index(b)) for a, b in EDGE_NAMES]


def load_patterns():
    """Returns (pattern_ids_per_word [n], unique_patterns [P, 12] uint8,
    counts [P], words list)."""
    ev = pq.read_table(DATA / "evidence.parquet")
    n = ev.num_rows
    Y = np.zeros((n, 12), dtype=np.uint8)
    for j, c in enumerate(DETECTORS):
        Y[:, j] = ev.column(c).to_numpy(zero_copy_only=False)
    Y[:, 11] = (ev.column("scowl_tier").to_numpy() > 0)
    # pack to ids
    weights = (1 << np.arange(12)).astype(np.int64)
    ids = Y @ weights
    uniq, inverse, counts = np.unique(ids, return_inverse=True,
                                      return_counts=True)
    P = len(uniq)
    pats = np.zeros((P, 12), dtype=np.uint8)
    for j in range(12):
        pats[:, j] = (uniq >> j) & 1
    words = ev.column("word").to_pylist()
    return inverse.astype(np.int32), pats, counts.astype(np.int64), words


def load_features():
    """Returns (X [n, d] float32 standardized+indicators, column names,
    scaler dict)."""
    ft = pq.read_table(DATA / "features.parquet")
    cols, names = [], []
    scaler = {}
    for c in FEATURES:
        v = ft.column(c).to_numpy(zero_copy_only=False).astype(np.float64)
        miss = ~np.isfinite(v)
        mu = float(np.nanmean(np.where(miss, np.nan, v)))
        sd = float(np.nanstd(np.where(miss, np.nan, v)))
        sd = sd if sd > 0 else 1.0
        z = (v - mu) / sd
        z[miss] = 0.0
        cols.append(z.astype(np.float32))
        names.append(c)
        scaler[c] = {"mean": mu, "sd": sd, "missing_rate": float(miss.mean())}
        if miss.any():
            cols.append(miss.astype(np.float32))
            names.append(c + "__missing")
    X = np.column_stack(cols)
    return X, names, scaler


def enumerate_cells(K: int = 12) -> np.ndarray:
    """All 2^K binary patterns, for exact normalization in S2 and for the
    capture-recapture all-zero extrapolation."""
    ids = np.arange(1 << K, dtype=np.int64)
    out = np.zeros((1 << K, K), dtype=np.uint8)
    for j in range(K):
        out[:, j] = (ids >> j) & 1
    return out


def save_fit(name: str, obj: dict) -> None:
    path = REPO / "research" / "model" / "fits" / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, sort_keys=True)


def load_fit(name: str) -> dict:
    path = REPO / "research" / "model" / "fits" / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)
