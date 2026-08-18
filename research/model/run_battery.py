"""
The Phase 3 heavy runner: real S4/S5 fits with the 50-start protocol, their
reduced simulation recovery (D-035), and S1's full identifiability battery.

Multi-start for the feature models honours §5.4's >= 50 initialisations as 50
SHORT runs (8 EM iterations) whose top three are refined to convergence — a
full 50 x 60-iteration battery over 9.79M rows would cost hours for the same
discrimination, and the short-run loglik ordering is what selects among
basins. Declared here, reported in MODEL_REPORT.md.

Reduced recovery for S4/S5: the real feature matrix X is held FIXED (it is
data, not a parameter), classes are drawn from the fitted prior, detectors
from the fitted class rates, and the refit must satisfy D-035's rate and
prevalence clauses. Prevalence for S4/S5 means realized class mass / n.
"""

from __future__ import annotations

import hashlib
import time

import numpy as np

from .data import (detector_names, edge_indices, load_features, load_fit,
                   load_patterns, save_fit)
from .em import fit_s1
from .features_model import _sigmoid, _softmax, fit_s4, fit_s5
from .identify import (fisher_condition_s1, multistart_s1, profile_s1)

TOL_RATE, TOL_PI_REL, REPS = 0.02, 0.05, 5


def _rng(seed: str) -> np.random.Generator:
    h = hashlib.sha256(seed.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(h[:8], "big")))


def log(msg):
    print(f"[battery] {msg}", flush=True)


def main():
    t0 = time.time()
    pat_ids, pats, counts, _ = load_patterns()
    X, feat_names, scaler = load_features()
    names = detector_names()
    ANCHOR = names.index("wiktionary_english")
    OCR_COL = feat_names.index("ocr_neighbor_freq_ratio")
    n = len(pat_ids)

    # ---- S4 real: 50 short + 3 refined --------------------------------------
    log("S4: 50 short starts")
    shorts = []
    for s in range(50):
        fit, _ = fit_s4(pat_ids, pats, X, seed=f"s4-{s}", max_iter=8,
                        anchor=ANCHOR)
        shorts.append((fit["loglik"], s))
    shorts.sort(reverse=True)
    log(f"S4 short logliks: best {shorts[0][0]:,.0f} worst {shorts[-1][0]:,.0f}")
    best_fit, best_post, refined = None, None, []
    for ll, s in shorts[:3]:
        fit, post = fit_s4(pat_ids, pats, X, seed=f"s4-{s}", max_iter=120,
                           anchor=ANCHOR)
        refined.append(fit["loglik"])
        if best_fit is None or fit["loglik"] > best_fit["loglik"]:
            best_fit, best_post = fit, post
    s4 = best_fit
    s4["multistart"] = {"n_starts": 50, "short_iters": 8,
                        "refined_logliks": refined,
                        "spread_refined": float(max(refined) - min(refined))}
    save_fit("s4_real", s4)
    np.save("research/data/s4_posterior.npy", best_post.astype(np.float32))
    log(f"S4 real: loglik {s4['loglik']:,.0f} | mean prior {s4['mean_prior']:.5f} "
        f"| implied words {best_post.sum():,.0f} | {time.time()-t0:.0f}s")

    # ---- S5 real ------------------------------------------------------------
    log("S5: 50 short starts")
    shorts = []
    for s in range(50):
        fit, _ = fit_s5(pat_ids, pats, X, OCR_COL, seed=f"s5-{s}", max_iter=8,
                        anchor=ANCHOR)
        shorts.append((fit["loglik"], s))
    shorts.sort(reverse=True)
    log(f"S5 short logliks: best {shorts[0][0]:,.0f} worst {shorts[-1][0]:,.0f}")
    best_fit, best_post, refined = None, None, []
    for ll, s in shorts[:3]:
        fit, post = fit_s5(pat_ids, pats, X, OCR_COL, seed=f"s5-{s}",
                           max_iter=120, anchor=ANCHOR)
        refined.append(fit["loglik"])
        if best_fit is None or fit["loglik"] > best_fit["loglik"]:
            best_fit, best_post = fit, post
    s5 = best_fit
    s5["multistart"] = {"n_starts": 50, "short_iters": 8,
                        "refined_logliks": refined,
                        "spread_refined": float(max(refined) - min(refined))}
    save_fit("s5_real", s5)
    np.save("research/data/s5_posterior.npy", best_post.astype(np.float32))
    log(f"S5 real: loglik {s5['loglik']:,.0f} | class mass "
        f"{[f'{m:,.0f}' for m in s5['class_mass']]} | {time.time()-t0:.0f}s")

    # ---- reduced recovery: S4 ------------------------------------------------
    log("S4 recovery (5 replicates, real X fixed)")
    rows = []
    Xb = np.column_stack([np.ones(n, dtype=np.float32), X])
    w = np.array(s4["w"]); a = np.array(s4["alpha"]); b = np.array(s4["beta"])
    prior = _sigmoid(Xb @ w)
    pf = pats.astype(np.float64)
    for r in range(REPS):
        g = _rng(f"s4rec:{r}")
        z = g.random(n) < prior
        fire = np.where(z[:, None], a[None, :], (1 - b)[None, :])
        Y = (g.random((n, 12)) < fire).astype(np.uint8)
        weights = (1 << np.arange(12)).astype(np.int64)
        uniq, inverse = np.unique(Y @ weights, return_inverse=True)
        rp = np.zeros((len(uniq), 12), dtype=np.uint8)
        for j in range(12):
            rp[:, j] = (uniq >> j) & 1
        fit, post = fit_s4(inverse.astype(np.int32), rp, X,
                           seed=f"s4recfit:{r}", max_iter=80, anchor=ANCHOR)
        rows.append({
            "replicate": r,
            "max_abs_alpha_err": float(np.max(np.abs(np.array(fit["alpha"]) - a))),
            "max_abs_beta_err": float(np.max(np.abs(np.array(fit["beta"]) - b))),
            "pi_rel_err": float(abs(post.sum() - z.sum()) / z.sum()),
        })
        log(f"  s4 r{r}: da {rows[-1]['max_abs_alpha_err']:.4f} "
            f"db {rows[-1]['max_abs_beta_err']:.4f} "
            f"pi_rel {rows[-1]['pi_rel_err']:.4f}")
    fails = [f"r{r['replicate']}" for r in rows
             if r["max_abs_alpha_err"] > TOL_RATE
             or r["max_abs_beta_err"] > TOL_RATE
             or r["pi_rel_err"] > TOL_PI_REL]
    s4_sr5 = "FIRES" if fails else "passes"
    log(f"S4 SR5 {s4_sr5}")

    # ---- reduced recovery: S5 ------------------------------------------------
    log("S5 recovery (5 replicates)")
    rates = np.stack([np.array(s5["rates_word"]), np.array(s5["rates_ocr"]),
                      np.array(s5["rates_neither"])])
    W = np.array(s5["W"])
    Z = np.zeros((n, 3), dtype=np.float64); Z[:, :2] = Xb @ W.T
    P = _softmax(Z)
    true_mass = np.array(s5["class_mass"])
    rows5 = []
    for r in range(REPS):
        g = _rng(f"s5rec:{r}")
        cum = P.cumsum(axis=1)
        uu = g.random(n)[:, None]
        z = (uu > cum).sum(axis=1)
        fire = rates[z]
        Y = (g.random((n, 12)) < fire).astype(np.uint8)
        weights = (1 << np.arange(12)).astype(np.int64)
        uniq, inverse = np.unique(Y @ weights, return_inverse=True)
        rp = np.zeros((len(uniq), 12), dtype=np.uint8)
        for j in range(12):
            rp[:, j] = (uniq >> j) & 1
        fit, post = fit_s5(inverse.astype(np.int32), rp, X, OCR_COL,
                           seed=f"s5recfit:{r}", max_iter=80, anchor=ANCHOR)
        fr = np.stack([np.array(fit["rates_word"]), np.array(fit["rates_ocr"]),
                       np.array(fit["rates_neither"])])
        mass = np.array(fit["class_mass"])
        drawn = np.bincount(z, minlength=3).astype(float)
        rows5.append({
            "replicate": r,
            "max_abs_rate_err": float(np.max(np.abs(fr - rates))),
            "word_mass_rel_err": float(abs(mass[0] - drawn[0]) / drawn[0]),
            "ocr_mass_rel_err": float(abs(mass[1] - drawn[1]) / max(drawn[1], 1)),
            "neither_mass_rel_err": float(abs(mass[2] - drawn[2]) / max(drawn[2], 1)),
        })
        log(f"  s5 r{r}: rate {rows5[-1]['max_abs_rate_err']:.4f} "
            f"massW {rows5[-1]['word_mass_rel_err']:.4f} "
            f"massO {rows5[-1]['ocr_mass_rel_err']:.4f} "
            f"massN {rows5[-1]['neither_mass_rel_err']:.4f}")
    fails5 = [f"r{r['replicate']}" for r in rows5
              if r["max_abs_rate_err"] > TOL_RATE
              or r["word_mass_rel_err"] > TOL_PI_REL
              or r["ocr_mass_rel_err"] > TOL_PI_REL
              or r["neither_mass_rel_err"] > TOL_PI_REL]
    s5_sr5 = "FIRES" if fails5 else "passes"
    log(f"S5 SR5 {s5_sr5}")

    save_fit("feature_recovery", {
        "s4": {"replicates": rows, "sr5": s4_sr5},
        "s5": {"replicates": rows5, "sr5": s5_sr5}})

    # ---- S1 full battery -----------------------------------------------------
    log("S1 battery: 50-start")
    ms, best_s1 = multistart_s1(pats, counts, ANCHOR)
    log(f"  multistart spread {ms['loglik_spread']:.4f} "
        f"distinct {ms['distinct_optima_at_0.01']} -> "
        f"{'pass' if ms['passes'] else 'FAIL'}")
    log("S1 battery: Fisher information")
    fi = fisher_condition_s1(pats, counts, best_s1)
    log(f"  rank {fi['rank']}/{fi['n_params']} cond {fi['condition_number']:.3e} "
        f"-> {'pass' if fi['passes'] else 'FAIL'}")
    log("S1 battery: 24 profile likelihoods")
    profiles = []
    for kind in ("alpha", "beta"):
        for k in range(12):
            pr = profile_s1(pats, counts, best_s1, kind, k)
            profiles.append(pr)
    flat = [p["param"] for p in profiles if not p["identified"]]
    log(f"  flat profiles: {flat if flat else 'none'}")
    save_fit("s1_battery", {"multistart": ms, "fisher": fi,
                            "profiles": profiles,
                            "sr4": "FIRES" if (flat or not ms["passes"]
                                               or not fi["passes"]) else "passes"})
    save_fit("s1_real", best_s1)     # the 50-start best replaces the single fit
    log(f"DONE in {(time.time()-t0)/60:.1f}m")


if __name__ == "__main__":
    main()
