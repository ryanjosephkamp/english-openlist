"""
The Phase 2 gate: held-out perplexity plus negative-control separation.

Separation is AUC (Mann-Whitney), one feature at a time, held-out positives
against each family — with the Hanley-McNeil standard error for a closed-form,
deterministic 95% interval. No bootstrap, no RNG.

SR3 is measured here, on its own terms: corpus-derived features on the OCR
family (restricted to corruptions Google Books actually contains — an artifact
the corpus never saw needs no separating) against RARE real words — held-out
positives in the bottom volume quartile. If every corpus feature's interval
covers 0.5, the corpus arm cannot tell scan artifacts from rare vocabulary and
SR3 FIRES.

Writes research/PHASE2_REPORT.md.  Run:  python -m research.features.gate_report
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date

import numpy as np
import pyarrow.parquet as pq

from research.ingest.common import REPO, read_derived
from . import charmodel, controls
from .partitions import DETECTOR_COLUMNS, MIN_DETECTORS, assign

DATA = REPO / "research" / "data"

FEATURES = ["orthotactic_logp_per_char", "ocr_neighbor_freq_ratio",
            "gb_tokens_per_volume", "gb_span_fill", "gb_log10_volume",
            "zipf_resid", "morph_productivity_vn"]
CORPUS_FEATURES = ["ocr_neighbor_freq_ratio", "gb_tokens_per_volume",
                   "gb_span_fill", "gb_log10_volume", "zipf_resid"]


def auc_ci(pos: np.ndarray, neg: np.ndarray):
    """AUC that positives score HIGHER, with Hanley-McNeil 95% CI. NaNs are
    dropped per side and the retained counts are reported."""
    pos = pos[~np.isnan(pos)]
    neg = neg[~np.isnan(neg)]
    n1, n2 = len(pos), len(neg)
    if n1 < 10 or n2 < 10:
        return None
    both = np.concatenate([pos, neg])
    ranks = both.argsort().argsort().astype(np.float64) + 1
    # average ranks for ties
    order = both.argsort()
    sorted_vals = both[order]
    avg = ranks.copy()
    i = 0
    while i < len(sorted_vals):
        j = i
        while j + 1 < len(sorted_vals) and sorted_vals[j + 1] == sorted_vals[i]:
            j += 1
        if j > i:
            avg[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    r1 = avg[:n1].sum()
    auc = (r1 - n1 * (n1 + 1) / 2) / (n1 * n2)
    q1 = auc / (2 - auc)
    q2 = 2 * auc**2 / (1 + auc)
    se = math.sqrt(max((auc * (1 - auc) + (n1 - 1) * (q1 - auc**2)
                        + (n2 - 1) * (q2 - auc**2)) / (n1 * n2), 1e-12))
    return {"auc": float(auc), "lo": float(auc - 1.96 * se),
            "hi": float(auc + 1.96 * se), "n_pos": n1, "n_neg": n2}


def orient(row, feature):
    """Report every AUC as P(positive ranks ABOVE negative) for features where
    high means word-like; flip the ocr ratio, where HIGH means artifact."""
    if row is None:
        return None
    if feature == "ocr_neighbor_freq_ratio":
        row = {**row, "auc": 1 - row["auc"], "lo": 1 - row["hi"], "hi": 1 - row["lo"]}
    return row


def main() -> int:
    feats = pq.read_table(DATA / "features.parquet")
    ev = pq.read_table(DATA / "evidence.parquet")
    words = feats.column("word").to_pylist()
    ix = {w: i for i, w in enumerate(words)}
    col = {name: feats.column(name).to_numpy(zero_copy_only=False)
           for name in FEATURES}
    gb_vol = ev.column("gb_total_volume").to_numpy()

    det_count = np.zeros(len(words), dtype=np.int8)
    for c in DETECTOR_COLUMNS:
        det_count += ev.column(c).to_numpy(zero_copy_only=False).astype(np.int8)
    det_count += (ev.column("scowl_tier").to_numpy() > 0).astype(np.int8)
    detector_hit_words = {w for i, w in enumerate(words) if det_count[i] > 0}

    pool = [w for i, w in enumerate(words) if det_count[i] >= MIN_DETECTORS]
    test_pos = [w for w in pool if assign(w) == "test"]

    # rebuild the char model exactly as build_features did (same seed, same pool)
    model = charmodel.CharModel()
    model.fit([w for w in pool if assign(w) == "train"])
    model.finalize()
    model.tune([w for w in pool if assign(w) == "dev"])

    reference = read_derived("wordnet") | read_derived("web2")
    gb_match_all = ev.column("gb_total_match").to_numpy()
    ref_match = {w: int(gb_match_all[ix[w]]) for w in reference if w in ix}
    all_keys = set()
    for sid in ("wordnet", "wiktionary_english", "wiktionary_titles", "web2",
                "hunspell_en_US", "hunspell_en_GB", "hunspell_en_CA",
                "hunspell_en_AU", "enable1", "sowpods_legacy", "nwl2023",
                "csw21", "scowl", "wordfreq"):
        all_keys |= read_derived(sid)

    families = {
        "ocr": controls.ocr_family(test_pos, reference),
        "pseudo": controls.pseudo_family(model, all_keys),
        "foreign": controls.foreign_family(detector_hit_words),
        "mw_refuted": controls.mw_family(),
    }

    def score_words(ws, feature):
        """Feature values for control words: from the matrix when the word is
        in-frame; recomputed live for out-of-frame corruptions/pseudo-words
        (orthotactics and OCR ratio only — corpus features need GB rows)."""
        vals = []
        for w in ws:
            i = ix.get(w)
            if i is not None:
                vals.append(col[feature][i])
            elif feature == "orthotactic_logp_per_char":
                vals.append(model.logp_word(w)[1])
            elif feature == "ocr_neighbor_freq_ratio":
                # computable live for out-of-frame corruptions/pseudo-words;
                # their own GB match is 0 by construction (not in the frame)
                best = np.nan
                from . import ocr as _ocr
                for nb, _pair in _ocr.detect_neighbors(w, reference):
                    r = np.log10(ref_match.get(nb, 0) + 1)
                    if np.isnan(best) or r > best:
                        best = r
                vals.append(best)
            else:
                vals.append(np.nan)
        return np.array(vals, dtype=np.float64)

    pos_sample = controls._rank(test_pos, "gate-positives")[:controls.FAMILY_SIZE]
    lines = [f"# Phase 2 gate — held-out perplexity and negative-control separation\n",
             f"Measured {date.today().isoformat()}.\n"]

    manifest = json.load(open(REPO / "research" / "features_manifest.json"))
    ppl = manifest["charmodel"]["perplexity_test"]
    lines.append(f"## Held-out perplexity\n")
    lines.append(f"Per-character perplexity on the {manifest['partitions']['test']:,}-word "
                 f"test partition: **{ppl:.3f}** (alphabet 27; uniform = 27; train-slice "
                 f"{manifest['charmodel']['perplexity_train_slice']:.3f}). "
                 f"Interpolation weights (uniform → order-4): "
                 f"{[round(l,4) for l in manifest['charmodel']['lambdas']]}.\n")

    lines.append("## Separation — AUC (positive ranks above family), Hanley-McNeil 95% CI\n")
    lines.append("| Family | n | Feature | AUC | 95% CI | kept n⁺/n⁻ |")
    lines.append("|---|---:|---|---:|---|---|")
    results = {}
    for fam, ws in families.items():
        for feature in FEATURES:
            r = orient(auc_ci(score_words(pos_sample, feature),
                              score_words(ws, feature)), feature)
            results[(fam, feature)] = r
            if r:
                lines.append(f"| {fam} | {len(ws):,} | `{feature}` | "
                             f"**{r['auc']:.3f}** | [{r['lo']:.3f}, {r['hi']:.3f}] "
                             f"| {r['n_pos']:,}/{r['n_neg']:,} |")
            else:
                lines.append(f"| {fam} | {len(ws):,} | `{feature}` | — | too few "
                             f"non-NaN values | |")

    # ---- SR3 ---------------------------------------------------------------
    ocr_in_gb = [w for w in families["ocr"]
                 if w in ix and gb_vol[ix[w]] > 0]
    pos_vol = np.array([gb_vol[ix[w]] for w in test_pos if w in ix])
    q25 = np.quantile(pos_vol[pos_vol > 0], 0.25)
    rare_pos = [w for w in test_pos
                if w in ix and 0 < gb_vol[ix[w]] <= q25]
    lines.append(f"\n## SR3 — can the corpus arm tell scan artifacts from rare "
                 f"real words?\n")
    lines.append(f"OCR corruptions Google Books actually contains: "
                 f"**{len(ocr_in_gb):,}** of {len(families['ocr']):,}. Rare "
                 f"real words (held-out positives, volume ≤ Q1 = {q25:.0f}): "
                 f"**{len(rare_pos):,}**.\n")
    lines.append("| Corpus feature | AUC (rare-real above artifact) | 95% CI |")
    lines.append("|---|---:|---|")
    sr3_separated = []
    for feature in CORPUS_FEATURES:
        r = orient(auc_ci(score_words(rare_pos, feature),
                          score_words(ocr_in_gb, feature)), feature)
        if r:
            sep = r["lo"] > 0.5 or r["hi"] < 0.5
            sr3_separated.append((feature, r, sep))
            lines.append(f"| `{feature}` | **{r['auc']:.3f}** | "
                         f"[{r['lo']:.3f}, {r['hi']:.3f}]"
                         f"{' — separates' if sep else ''} |")
    fires = not any(sep for _, _, sep in sr3_separated)
    lines.append(f"\n**SR3 {'FIRES — no corpus feature separates' if fires else 'passes'}**: "
                 + ("every interval covers 0.5." if fires else
                    ", ".join(f"`{f}`" for f, _, s in sr3_separated if s)
                    + " exclude 0.5.") + "\n")

    # ---- the typed-neighbour asymmetry, stated as rates -------------------
    # The AUC rows for ocr_neighbor_freq_ratio starve on NaN for most families,
    # and that is the feature WORKING: it is a near-binary artifact flag. The
    # honest presentation is the firing rate per family.
    lines.append("\n## The typed-neighbour asymmetry (D-012)\n")
    lines.append("Share of words with ANY typed OCR back-neighbour in the "
                 "reference lexicon — the number Phase 0 could not get from raw "
                 "edit distance, which fired on 50.5% of a real-word control:\n")
    lines.append("| Set | Fires | Rate |")
    lines.append("|---|---:|---:|")
    hits_col = feats.column("ocr_neighbor_hits").to_numpy()
    for label, ws in [("held-out positives", pos_sample)] + list(families.items()):
        k = 0
        for w in ws:
            i = ix.get(w)
            if i is not None:
                k += int(hits_col[i] > 0)
            else:
                k += int(any(True for _ in controls.ocr.detect_neighbors(w, reference)))
        lines.append(f"| {label} | {k:,}/{len(ws):,} | {100*k/len(ws):.1f}% |")

    fam_sizes = {k: len(v) for k, v in families.items()}
    lines.append(f"\nFamily sizes: {fam_sizes}. Positives: {len(pos_sample):,} "
                 f"of {len(test_pos):,} held-out test words, sha256-selected.\n")

    out = REPO / "research" / "PHASE2_REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    with open(REPO / "research" / "phase2_gate.json", "w") as f:
        json.dump({"perplexity_test": ppl, "sr3_fires": fires,
                   "families": fam_sizes,
                   "auc": {f"{k[0]}:{k[1]}": v for k, v in results.items() if v}},
                  f, indent=2)
    print(f"SR3: {'FIRES' if fires else 'passes'}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
