"""
The simulation gate — SR5, with D-035's tolerance applied verbatim.

Parametric bootstrap at the observed scale: for each specification, take its
REAL-data fit as truth, generate five replicate worlds of 9,787,841 pattern
draws from that truth, refit from a fresh seed, relabel per D-034, and check
every replicate against the tolerance. Generation is exact — class-conditional
cell probabilities are enumerated over all 4,096 cells, and the world is one
multinomial draw — so the only randomness is the draw itself, seeded from
sha256 so the worlds are bit-reproducible.

Also runs, reports, and does NOT gate: the misspecification cross — S1 fitted
to S2's worlds — which measures what ignoring the declared dependence costs.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np

from .data import enumerate_cells, edge_indices, save_fit
from .em import fit_s1, pattern_loglik
from .loglinear import S2Model
from .randeff import fit_s3, _pattern_logp, _quad

N_FRAME = 9_787_841
REPLICATES = 5
TOL_RATE = 0.02          # D-035
TOL_PI_REL = 0.05
TOL_LAMBDA = 0.15


def _rng(seed: str) -> np.random.Generator:
    h = hashlib.sha256(seed.encode()).digest()
    return np.random.Generator(np.random.PCG64(int.from_bytes(h[:8], "big")))


def cell_probs_s1(fit, cells):
    a = np.array(fit["alpha"]); b = np.array(fit["beta"])
    la, lb = pattern_loglik(cells, a, b)
    return fit["pi"] * np.exp(la) + (1 - fit["pi"]) * np.exp(lb)


def cell_probs_s2(fit, model):
    pw = np.exp(model.class_logp(np.array(fit["theta_word"]),
                                 np.array(fit["lambda_word"])))
    pn = np.exp(model.class_logp(np.array(fit["theta_non"]),
                                 np.array(fit["lambda_non"])))
    return fit["pi"] * pw + (1 - fit["pi"]) * pn


def cell_probs_s3(fit, cells):
    nodes, wts = _quad()
    aw = np.array(fit["a_word"]); an = np.array(fit["a_non"])
    b = np.array(fit["loadings"])
    lw = _pattern_logp(cells, aw, b, nodes, wts)
    ln = _pattern_logp(cells, an, b, nodes, wts)
    return fit["pi"] * np.exp(lw) + (1 - fit["pi"]) * np.exp(ln)


def draw_world(probs, seed):
    counts = _rng(seed).multinomial(N_FRAME, probs / probs.sum())
    keep = counts > 0
    return keep, counts


def recover_s1(truth, cells, anchor):
    rows = []
    for r in range(REPLICATES):
        keep, counts = draw_world(cell_probs_s1(truth, cells), f"simw:s1:{r}")
        fit = fit_s1(cells[keep], counts[keep], seed=f"simfit:s1:{r}",
                     anchor=anchor)
        rows.append({
            "replicate": r,
            "max_abs_alpha_err": float(np.max(np.abs(
                np.array(fit["alpha"]) - np.array(truth["alpha"])))),
            "max_abs_beta_err": float(np.max(np.abs(
                np.array(fit["beta"]) - np.array(truth["beta"])))),
            "pi_rel_err": float(abs(fit["pi"] - truth["pi"]) / truth["pi"]),
        })
    return rows


def recover_s2(truth, model, cells, anchor):
    rows = []
    for r in range(REPLICATES):
        keep, counts = draw_world(cell_probs_s2(truth, model), f"simw:s2:{r}")
        fit = model.fit(cells[keep].astype(np.uint8), counts[keep],
                        seed=f"simfit:s2:{r}", anchor=anchor)
        rows.append({
            "replicate": r,
            "max_abs_alpha_err": float(np.max(np.abs(
                np.array(fit["alpha_marginal"])
                - np.array(truth["alpha_marginal"])))),
            "max_abs_beta_err": float(np.max(np.abs(
                np.array(fit["beta_marginal"])
                - np.array(truth["beta_marginal"])))),
            "pi_rel_err": float(abs(fit["pi"] - truth["pi"]) / truth["pi"]),
            "max_abs_lambda_err": float(max(
                np.max(np.abs(np.array(fit["lambda_word"])
                              - np.array(truth["lambda_word"]))),
                np.max(np.abs(np.array(fit["lambda_non"])
                              - np.array(truth["lambda_non"]))))),
        })
    return rows


def recover_s3(truth, cells, anchor):
    rows = []
    for r in range(REPLICATES):
        keep, counts = draw_world(cell_probs_s3(truth, cells), f"simw:s3:{r}")
        fit = fit_s3(cells[keep], counts[keep], seed=f"simfit:s3:{r}",
                     anchor=anchor)
        rows.append({
            "replicate": r,
            "max_abs_alpha_err": float(np.max(np.abs(
                np.array(fit["alpha_marginal"])
                - np.array(truth["alpha_marginal"])))),
            "max_abs_beta_err": float(np.max(np.abs(
                np.array(fit["beta_marginal"])
                - np.array(truth["beta_marginal"])))),
            "pi_rel_err": float(abs(fit["pi"] - truth["pi"])
                                / max(truth["pi"], 1e-9)),
            "converged": fit["converged"],
        })
    return rows


def misspec_cross(s2_truth, model, cells, anchor):
    """S1 fitted to S2 worlds — reported, never gated (D-035)."""
    rows = []
    for r in range(REPLICATES):
        keep, counts = draw_world(cell_probs_s2(s2_truth, model),
                                  f"simw:cross:{r}")
        fit = fit_s1(cells[keep], counts[keep], seed=f"simfit:cross:{r}",
                     anchor=anchor)
        rows.append({
            "replicate": r,
            "pi_fit": fit["pi"], "pi_truth": s2_truth["pi"],
            "max_abs_alpha_err": float(np.max(np.abs(
                np.array(fit["alpha"])
                - np.array(s2_truth["alpha_marginal"])))),
            "max_abs_beta_err": float(np.max(np.abs(
                np.array(fit["beta"])
                - np.array(s2_truth["beta_marginal"])))),
        })
    return rows


def verdict(rows, spec):
    fails = []
    for row in rows:
        if row["max_abs_alpha_err"] > TOL_RATE:
            fails.append(f"r{row['replicate']}: alpha {row['max_abs_alpha_err']:.4f}")
        if row["max_abs_beta_err"] > TOL_RATE:
            fails.append(f"r{row['replicate']}: beta {row['max_abs_beta_err']:.4f}")
        if row["pi_rel_err"] > TOL_PI_REL:
            fails.append(f"r{row['replicate']}: pi rel {row['pi_rel_err']:.4f}")
        if spec == "s2" and row.get("max_abs_lambda_err", 0) > TOL_LAMBDA:
            fails.append(f"r{row['replicate']}: lambda {row['max_abs_lambda_err']:.4f}")
    return fails


def main():
    from .data import load_patterns, detector_names, load_fit
    _, pats, counts, _ = load_patterns()
    cells = enumerate_cells(12)
    anchor = detector_names().index("wiktionary_english")
    model = S2Model(12, edge_indices())

    out = {}
    for spec, fn in (("s1", lambda t: recover_s1(t, cells, anchor)),
                     ("s2", lambda t: recover_s2(t, model, cells, anchor)),
                     ("s3", lambda t: recover_s3(t, cells, anchor))):
        truth = load_fit(f"{spec}_real")
        rows = fn(truth)
        fails = verdict(rows, spec)
        out[spec] = {"replicates": rows, "failures": fails,
                     "sr5": "FIRES" if fails else "passes"}
        print(f"[sim] {spec}: SR5 {'FIRES — ' + '; '.join(fails) if fails else 'passes'}",
              flush=True)

    out["misspec_cross_s1_on_s2"] = misspec_cross(
        load_fit("s2_real"), model, cells, anchor)
    save_fit("simulation_gate", out)
    print("[sim] saved fits/simulation_gate.json", flush=True)


if __name__ == "__main__":
    main()
