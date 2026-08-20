"""
The identifiability battery — PROTOCOL §5, all five checks.

A model that cannot identify its parameters is reported as non-identified,
not fitted anyway (SR4). The battery does not trust the optimiser: a returned
number is not an identified number until the curvature says so, the profile
says so, and fifty restarts say so.

  5.1 degrees of freedom — table only; at K=12 never the binding constraint.
  5.2 Fisher information — numerical Hessian of the collapsed log-likelihood
      at the optimum, on the LOGIT scale (D-034: boundary-adjacent rates make
      raw-scale curvature meaningless); rank and condition number against the
      declared 1e8 threshold.
  5.3 profile likelihood — for every alpha_k and beta_k: fix the parameter on
      a grid, re-optimise everything else, report the profile's curvature. A
      flat profile (drop < 2.0 log-lik units across ±0.05) is non-identified.
  5.4 multi-start — 50 sha256-seeded initialisations; all must reach the same
      optimum modulo label switching (loglik spread < 1.0 after relabel).
  5.5 simulation recovery at observed sparsity — simulate.py, gated by D-035.
"""

from __future__ import annotations

import numpy as np

from .data import save_fit
from .em import e_step, fit_s1, log_prior, m_step

PROFILE_GRID = np.array([-0.05, -0.02, 0.02, 0.05])
FLAT_DROP = 2.0
COND_THRESHOLD = 1e8      # D-034, logit scale


def logit(p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return np.log(p / (1 - p))


def s1_loglik_at(pats, counts, pi, alpha, beta):
    _, ll = e_step(pats, counts, pi, alpha, beta)
    return ll + log_prior(pi, alpha, beta)


def fisher_condition_s1(pats, counts, fit):
    """Numerical Hessian on logit-transformed (pi, alpha, beta)."""
    x0 = np.concatenate([[logit(fit["pi"])], logit(np.array(fit["alpha"])),
                         logit(np.array(fit["beta"]))])

    def f(x):
        pi = 1 / (1 + np.exp(-x[0]))
        a = 1 / (1 + np.exp(-x[1:13]))
        b = 1 / (1 + np.exp(-x[13:]))
        return s1_loglik_at(pats, counts, pi, a, b)

    n = len(x0)
    h = 1e-4
    H = np.zeros((n, n))
    f0 = f(x0)
    for i in range(n):
        for j in range(i, n):
            xi = x0.copy(); xi[i] += h; xi[j] += h; fpp = f(xi)
            xi = x0.copy(); xi[i] += h; xi[j] -= h; fpm = f(xi)
            xi = x0.copy(); xi[i] -= h; xi[j] += h; fmp = f(xi)
            xi = x0.copy(); xi[i] -= h; xi[j] -= h; fmm = f(xi)
            H[i, j] = H[j, i] = (fpp - fpm - fmp + fmm) / (4 * h * h)
    info = -H
    eig = np.linalg.eigvalsh(info)
    rank = int((eig > eig.max() * 1e-12).sum())
    cond = float(eig.max() / max(eig.min(), 1e-300)) if eig.min() > 0 else float("inf")
    return {"rank": rank, "n_params": n, "condition_number": cond,
            "min_eig": float(eig.min()), "max_eig": float(eig.max()),
            "passes": bool(eig.min() > 0 and cond < COND_THRESHOLD)}


def profile_s1(pats, counts, fit, param_kind: str, k: int):
    """Profile one rate: fix it at optimum+delta, EM over the rest."""
    base = fit["logpost"]
    drops = []
    for d in PROFILE_GRID:
        pi = fit["pi"]
        alpha = np.array(fit["alpha"]).copy()
        beta = np.array(fit["beta"]).copy()
        fixed = np.clip((alpha[k] if param_kind == "alpha" else beta[k]) + d,
                        1e-6, 1 - 1e-6)
        prev = -np.inf
        for _ in range(300):
            if param_kind == "alpha":
                alpha[k] = fixed
            else:
                beta[k] = fixed
            post, ll = e_step(pats, counts, pi, alpha, beta)
            pi, alpha, beta = m_step(pats, counts, post)
            if param_kind == "alpha":
                alpha[k] = fixed
            else:
                beta[k] = fixed
            obj = s1_loglik_at(pats, counts, pi, alpha, beta)
            if abs(obj - prev) < 1e-8 * max(1.0, abs(prev)):
                break
            prev = obj
        drops.append(base - obj)
    max_drop = float(max(drops))
    return {"param": f"{param_kind}[{k}]", "drops": [float(x) for x in drops],
            "max_drop": max_drop, "identified": bool(max_drop > FLAT_DROP)}


def multistart_s1(pats, counts, anchor, n_starts: int = 50):
    logliks, keys = [], []
    best = None
    for s in range(n_starts):
        fit = fit_s1(pats, counts, seed=f"s1-ms-{s}", anchor=anchor)
        logliks.append(fit["logpost"])
        keys.append(round(fit["logpost"], 2))
        if best is None or fit["logpost"] > best["logpost"]:
            best = fit
    spread = float(max(logliks) - min(logliks))
    distinct = len(set(keys))
    return {"n_starts": n_starts, "loglik_spread": spread,
            "distinct_optima_at_0.01": distinct,
            "passes": bool(spread < 1.0), "best_logpost": float(max(logliks)),
            "all_logliks_summary": {
                "min": float(min(logliks)), "max": float(max(logliks))}}, best
