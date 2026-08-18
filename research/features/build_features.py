"""
Drive the Phase 2 feature build.

Reads research/data/evidence.parquet, computes every §3.2 channel, writes
research/data/features.parquet keyed to the SAME word order, and records every
hyperparameter, seed, count and deviation in research/features_manifest.json —
the committed record Phase 3 and Phase 4 read.

Honest limitations, stated here and in the manifest rather than discovered:

  * Gries's DP and Juilland's D are NOT computed. Both need per-part
    frequencies (documents, or at least per-year counts), and the Google Books
    ingest kept year-LEVEL AGGREGATES only. What the aggregates support —
    year_count, span fill, tokens-per-volume, volumes-per-year — ships as
    dispersion PROXIES, named as such.
  * Baayen's P uses volume-hapaxes (total_volume == 1), because the 2020
    corpus ships no types below its occurrence floor, so match-count hapaxes
    cannot exist. The min_match_seen column in the affix table shows the floor.

Run:  python -m research.features.build_features
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from research.ingest.common import REPO, read_derived
from . import charmodel, ocr, productivity
from .partitions import (DETECTOR_COLUMNS, MIN_DETECTORS, SEED, TRAIN_END,
                         DEV_END, assign)

DATA = REPO / "research" / "data"


def log(msg):
    print(f"[features] {msg}", flush=True)


def main() -> int:
    t0 = time.time()
    ev = pq.read_table(DATA / "evidence.parquet")
    words = ev.column("word").to_pylist()
    n = len(words)
    log(f"frame: {n:,} words")

    det_count = np.zeros(n, dtype=np.int8)
    for c in DETECTOR_COLUMNS:
        det_count += ev.column(c).to_numpy(zero_copy_only=False).astype(np.int8)
    det_count += (ev.column("scowl_tier").to_numpy() > 0).astype(np.int8)

    gb_match = ev.column("gb_total_match").to_numpy()
    gb_volume = ev.column("gb_total_volume").to_numpy()
    gb_first = ev.column("gb_first_year").to_numpy()
    gb_last = ev.column("gb_last_year").to_numpy()
    gb_years = ev.column("gb_year_count").to_numpy()

    # -- partitions (leakage discipline, §3.3) -------------------------------
    pool_idx = np.flatnonzero(det_count >= MIN_DETECTORS)
    pool = [words[i] for i in pool_idx]
    parts = {"train": [], "dev": [], "test": []}
    for w in pool:
        parts[assign(w)].append(w)
    log(f"strong-positive pool (>= {MIN_DETECTORS}/12 detectors): {len(pool):,} "
        f"-> train {len(parts['train']):,} / dev {len(parts['dev']):,} / "
        f"test {len(parts['test']):,}")

    # -- orthotactic channel -------------------------------------------------
    model = charmodel.CharModel()
    model.fit(parts["train"])
    model.finalize()
    lambdas = model.tune(parts["dev"])
    log(f"char model lambdas (uniform..order4): {[round(l,4) for l in lambdas]}")
    ppl_test = model.perplexity(parts["test"])
    ppl_train = model.perplexity(parts["train"][: len(parts['test'])])
    log(f"perplexity: held-out test {ppl_test:.3f} | train slice {ppl_train:.3f}")

    logp_total = np.empty(n, dtype=np.float32)
    logp_char = np.empty(n, dtype=np.float32)
    t1 = time.time()
    for i, w in enumerate(words):
        lt, lc = model.logp_word(w)
        logp_total[i] = lt
        logp_char[i] = lc
        if i % 2_000_000 == 0 and i:
            log(f"  orthotactics {i:,}/{n:,} ({time.time()-t1:.0f}s)")
    log(f"orthotactic scores in {time.time()-t1:.0f}s")

    # -- reference lexicon ---------------------------------------------------
    reference = read_derived("wordnet") | read_derived("web2")
    log(f"reference lexicon (wordnet u web2): {len(reference):,}")

    # -- typed OCR neighbourhood --------------------------------------------
    word_ix = {w: i for i, w in enumerate(words)}
    ref_match = {w: int(gb_match[word_ix[w]]) for w in reference if w in word_ix}
    hits = np.zeros(n, dtype=np.int8)
    ratio = np.full(n, np.nan, dtype=np.float32)
    t1 = time.time()
    for i, w in enumerate(words):
        best = None
        k = 0
        for neighbor, _pair in ocr.detect_neighbors(w, reference):
            k += 1
            nm = ref_match.get(neighbor, 0)
            r = np.log10((nm + 1) / (int(gb_match[i]) + 1))
            if best is None or r > best:
                best = r
        hits[i] = min(k, 127)
        if best is not None:
            ratio[i] = best
        if i % 2_000_000 == 0 and i:
            log(f"  ocr {i:,}/{n:,} ({time.time()-t1:.0f}s)")
    log(f"ocr neighbourhood in {time.time()-t1:.0f}s")

    # -- productivity over the FULL GB aggregate -----------------------------
    gb = pq.read_table(DATA.parent.parent / ".cache" / "sources" / "derived"
                       / "google_books_1grams.parquet")
    t1 = time.time()
    table = productivity.affix_table(
        gb.column("word").to_pylist(),
        gb.column("total_match").to_numpy(),
        gb.column("total_volume").to_numpy(),
        reference)
    log(f"affix table over {gb.num_rows:,} GB types in {time.time()-t1:.0f}s")
    with open(REPO / "research" / "productivity_table.json", "w") as f:
        json.dump({f"{k[0]}:{k[1]}": v for k, v in table.items()}, f, indent=2)

    suffix_p = {s: table[("suffix", s)]["P_vn"] for s in productivity.SUFFIXES}
    morph_p = np.full(n, np.nan, dtype=np.float32)
    has_parse = np.zeros(n, dtype=bool)
    t1 = time.time()
    for i, w in enumerate(words):
        ps = productivity.parse_suffix(w, reference)
        if ps and suffix_p.get(ps[0]) is not None:
            morph_p[i] = suffix_p[ps[0]]
            has_parse[i] = True
    log(f"per-word productivity in {time.time()-t1:.0f}s "
        f"({int(has_parse.sum()):,} parsed)")

    # -- dispersion proxies (what year-level aggregates CAN support) ---------
    has_gb = gb_match > 0
    span = np.where(has_gb, gb_last - gb_first + 1, 0).astype(np.int16)
    span_fill = np.where(span > 0, gb_years / np.maximum(span, 1), np.nan)
    tokens_per_volume = np.where(gb_volume > 0, gb_match / np.maximum(gb_volume, 1), np.nan)
    volumes_per_year = np.where(gb_years > 0, gb_volume / np.maximum(gb_years, 1), np.nan)
    log10_match = np.where(has_gb, np.log10(np.maximum(gb_match, 1)), np.nan)
    log10_volume = np.where(gb_volume > 0, np.log10(gb_volume), np.nan)

    # -- Zipf-Mandelbrot conformity over the full aggregate ------------------
    agg_match = gb.column("total_match").to_numpy()
    order = np.sort(agg_match)[::-1].astype(np.float64)
    R = len(order)
    probe_ranks = np.unique(np.geomspace(1, R, 400).astype(np.int64))
    probe_f = order[probe_ranks - 1]
    keep = probe_f > 0
    pr, pf = probe_ranks[keep].astype(np.float64), probe_f[keep]
    best = None
    for beta in (0.0, 1.0, 2.7, 5.0, 10.0, 26.0, 100.0, 1000.0):
        X = np.vstack([np.ones_like(pr), np.log10(pr + beta)]).T
        y = np.log10(pf)
        coef, res, *_ = np.linalg.lstsq(X, y, rcond=None)
        sse = float(res[0]) if len(res) else float(((X @ coef - y) ** 2).sum())
        if best is None or sse < best[0]:
            best = (sse, beta, coef)
    sse, beta, (logC, neg_alpha) = best
    alpha = -neg_alpha
    log(f"Zipf-Mandelbrot fit: alpha={alpha:.4f} beta={beta} logC={logC:.3f} sse={sse:.4f}")
    # rank of each frame word among all GB types (ties share a rank)
    rank = np.full(n, 0, dtype=np.int64)
    m = gb_match[has_gb].astype(np.float64)
    rank_vals = R - np.searchsorted(np.sort(agg_match), gb_match[has_gb], side="right") + 1
    rank[has_gb] = rank_vals
    zipf_rank = np.where(has_gb, np.log10(np.maximum(rank, 1)), np.nan)
    pred = logC - alpha * np.log10(np.maximum(rank, 1) + beta)
    zipf_resid = np.where(has_gb, log10_match - pred, np.nan)

    # -- write ---------------------------------------------------------------
    out = pa.table({
        "word": words,
        "orthotactic_logp_total": logp_total,
        "orthotactic_logp_per_char": logp_char,
        "ocr_neighbor_hits": hits,
        "ocr_neighbor_freq_ratio": ratio,
        "morph_productivity_vn": morph_p,
        "morph_has_parse": has_parse,
        "gb_year_span": span,
        "gb_span_fill": span_fill.astype(np.float32),
        "gb_tokens_per_volume": tokens_per_volume.astype(np.float32),
        "gb_volumes_per_year": volumes_per_year.astype(np.float32),
        "gb_log10_match": log10_match.astype(np.float32),
        "gb_log10_volume": log10_volume.astype(np.float32),
        "zipf_log10_rank": zipf_rank.astype(np.float32),
        "zipf_resid": zipf_resid.astype(np.float32),
    })
    pq.write_table(out, DATA / "features.parquet", compression="zstd")

    manifest = {
        "built": date.today().isoformat(),
        "frame_rows": n,
        "partitions": {
            "seed": SEED, "rule": f"sha256(seed:word) unit in [0,1): "
            f"train<{TRAIN_END}, dev<{DEV_END}, else test",
            "pool_rule": f">= {MIN_DETECTORS} of 12 binary detectors",
            "pool": len(pool), "train": len(parts["train"]),
            "dev": len(parts["dev"]), "test": len(parts["test"]),
            "phase4_exclusion": "calibration items must exclude train+dev; "
                                "re-derive by seed and rule above",
        },
        "charmodel": {"order": charmodel.ORDER, "lambdas": lambdas,
                      "trained_on": "train types only",
                      "perplexity_test": ppl_test,
                      "perplexity_train_slice": ppl_train},
        "reference_lexicon": "wordnet u web2",
        "ocr_pairs": ocr.CONFUSIONS,
        "productivity": {
            "measure": "REALIZED productivity V/N per affix (Baayen type-count "
                       "family), NOT potential productivity P = n1/N",
            "why": "the GB 2020 floor is 40 on match AND volume (both minima "
                   "measured); hapaxes do not exist in the corpus under any "
                   "definition, so P is not computable — the censoring is "
                   "visible in the table's zero hapax columns",
            "table": "research/productivity_table.json",
        },
        "dispersion": {
            "computed": ["gb_year_span", "gb_span_fill", "gb_tokens_per_volume",
                         "gb_volumes_per_year", "gb_log10_match", "gb_log10_volume"],
            "not_computable": "Gries DP, Juilland D — need per-part counts; "
                              "the ingest kept year-level totals only",
        },
        "zipf": {"alpha": alpha, "beta": beta, "logC": logC, "sse": sse,
                 "fit_points": int(len(pr)), "population": int(R)},
        "feature_detector_dependence": "reference lexicon and pool overlap the "
            "wordnet/web2 detector columns; declared for S4/S5 conditioning",
    }
    with open(REPO / "research" / "features_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    log(f"wrote features.parquet ({(DATA/'features.parquet').stat().st_size/1e6:.1f} MB) "
        f"+ manifest in {time.time()-t0:.0f}s total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
