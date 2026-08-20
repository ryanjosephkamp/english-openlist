"""
The Phase 3 pilot: per-word posteriors from the selected specification, the
stratum summaries pre-registration needs, and the held-out comparison.

The current valid list is a TEST SET, never a fitting target (D-004): its
agreement rate is reported as a result, and disagreements are binned by
evidence pattern so Phase 4 can look at the right words.

Outputs:
    research/data/posteriors.parquet      word, p_word (+ p_ocr, p_neither)
    research/model/fits/pilot.json        every summary the report quotes
"""

from __future__ import annotations

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from research.ingest.common import FRAME_DIR
from .data import DATA, detector_names, load_fit, load_patterns, save_fit


def main(selected: str = "s4"):
    pat_ids, pats, counts, words = load_patterns()
    n = len(words)

    if selected == "s4":
        post_w = np.load(DATA / "s4_posterior.npy").astype(np.float64)
        p_ocr = None
    elif selected == "s5":
        P = np.load(DATA / "s5_posterior.npy").astype(np.float64)
        post_w, p_ocr = P[:, 0], P[:, 1]
    else:
        fit = load_fit(f"{selected}_real")
        post_w = np.array(fit["posterior_by_pattern"])[pat_ids]
        p_ocr = None

    cols = {"word": words, "p_word": post_w.astype(np.float32)}
    if p_ocr is not None:
        cols["p_ocr"] = p_ocr.astype(np.float32)
    pq.write_table(pa.table(cols), DATA / "posteriors.parquet",
                   compression="zstd")

    # ---- strata -------------------------------------------------------------
    names = detector_names()
    det_count = pats.sum(axis=1)[pat_ids]
    ev = pq.read_table(DATA / "evidence.parquet",
                       columns=["gb_total_match", "wordfreq_zipf"])
    has_gb = ev.column("gb_total_match").to_numpy() > 0
    has_wf = ~np.isnan(ev.column("wordfreq_zipf").to_numpy(zero_copy_only=False))
    no_evidence = (det_count == 0) & ~has_gb & ~has_wf

    def summarize(mask, label):
        p = post_w[mask]
        if len(p) == 0:
            return {"stratum": label, "n": 0}
        qs = np.quantile(p, [0.05, 0.25, 0.5, 0.75, 0.95])
        return {"stratum": label, "n": int(mask.sum()),
                "mean": float(p.mean()),
                "q05": float(qs[0]), "q25": float(qs[1]), "med": float(qs[2]),
                "q75": float(qs[3]), "q95": float(qs[4]),
                "share_gt_half": float((p > 0.5).mean()),
                "expected_words": float(p.sum())}

    strata = [
        summarize(np.ones(n, bool), "frame"),
        summarize(det_count == 0, "all-zero binary"),
        summarize(no_evidence, "no evidence of any kind (D-032)"),
        summarize((det_count == 0) & has_gb, "all-zero with GB data"),
        summarize(det_count >= 8, "strong positives (>=8 detectors)"),
        summarize((det_count >= 1) & (det_count <= 2), "thin evidence (1-2)"),
    ]

    # ---- decile table for Phase 4 stratification ---------------------------
    edges = np.quantile(post_w, np.linspace(0, 1, 11))
    deciles = [{"decile": i + 1, "lo": float(edges[i]), "hi": float(edges[i+1]),
                "n": int(((post_w >= edges[i]) &
                          (post_w <= edges[i+1] if i == 9 else
                           post_w < edges[i+1])).sum())}
               for i in range(10)]

    # ---- held-out agreement -------------------------------------------------
    valid = {w.strip() for w in open(FRAME_DIR / "merged_valid_words.txt",
                                     encoding="utf-8")}
    is_valid = np.fromiter((w in valid for w in words), bool, n)
    pred = post_w > 0.5
    agree = float((pred == is_valid).mean())
    val_and_pred = float((pred & is_valid).sum())
    val_not_pred = float((~pred & is_valid).sum())
    pred_not_val = float((pred & ~is_valid).sum())

    # disagreements binned by pattern
    dis = pred != is_valid
    dis_patterns = {}
    for pid in np.unique(pat_ids[dis]):
        mask = dis & (pat_ids == pid)
        key = "+".join(names[j] for j in range(12) if pats[pid, j]) or "all-zero"
        dis_patterns[key] = {
            "n": int(mask.sum()),
            "valid_but_low_p": int((mask & is_valid).sum()),
            "invalid_but_high_p": int((mask & ~is_valid).sum()),
            "mean_p": float(post_w[mask].mean()),
        }
    top_dis = dict(sorted(dis_patterns.items(),
                          key=lambda kv: -kv[1]["n"])[:15])

    pilot = {
        "selected_specification": selected,
        "strata": strata, "posterior_deciles": deciles,
        "held_out_agreement": {
            "rate_at_0.5": agree,
            "valid_and_predicted": val_and_pred,
            "valid_not_predicted": val_not_pred,
            "predicted_not_valid": pred_not_val,
            "n_valid": int(is_valid.sum()),
            "note": "the valid list is a drifting held-out test set at the "
                    "pinned revision; agreement is a RESULT, never a target",
        },
        "top_disagreement_patterns": top_dis,
    }
    save_fit("pilot", pilot)
    print(f"[pilot] wrote posteriors.parquet + fits/pilot.json "
          f"(spec {selected}, agreement {agree:.4f})")
    return pilot


if __name__ == "__main__":
    main()
