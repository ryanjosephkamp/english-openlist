"""
S3 — random-effects latent class (Qu, Tan & Kutner's family).

Within class c, a word carries a latent difficulty u ~ N(0,1), and detector k
fires with probability Φ(a_kc + b_k · u): the loading b_k lets residual
dependence — everything the declared edges do not capture — flow through a
single shared dimension instead of being forced into the rates.

The marginal pattern probability integrates u out by Gauss–Hermite quadrature
(21 nodes — exact for polynomial integrands up to degree 41, far beyond what
a 12-detector probit product needs). The whole marginal likelihood is then
maximized directly by L-BFGS on transformed parameters; with 677 patterns and
21 nodes the objective is a [677 × 21] broadcast, microseconds per call.

Loadings are shared across classes (b_k, not b_kc): the QTK parameterisation
that keeps the parameter count at 2K + K + 1 = 37 and, more importantly,
keeps the two classes' dependence structure comparable — a class-specific
loading would let the WORD class absorb dependence the NONWORD class cannot,
which is exactly the asymmetry the identifiability battery could not then
distinguish from label drift.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.special import log_ndtr
from scipy.stats import norm

from .em import seeded_uniform

NODES = 21


def _quad():
    x, w = np.polynomial.hermite_e.hermegauss(NODES)   # weight e^{-x²/2}
    return x, w / w.sum()


def _pattern_logp(pats, a, b, nodes, wts):
    """log P(pattern | class) marginal over u. pats [P,K]; a [K]; b [K]."""
    eta = a[None, :, None] + b[None, :, None] * nodes[None, None, :]  # [1,K,Q]
    lp1 = log_ndtr(eta)          # log Φ
    lp0 = log_ndtr(-eta)
    y = pats[:, :, None].astype(np.float64)                            # [P,K,1]
    s = (y * lp1 + (1 - y) * lp0).sum(axis=1)                          # [P,Q]
    m = s.max(axis=1, keepdims=True)
    return (m + np.log((np.exp(s - m) * wts[None, :]).sum(axis=1,
                                                          keepdims=True)))[:, 0]


def fit_s3(pats, counts, seed: str = "s3", anchor: int = 1):
    K = pats.shape[1]
    nodes, wts = _quad()
    u = seeded_uniform(seed, 2 * K + K + 1)
    a_w = norm.ppf(np.clip(0.55 + 0.4 * u[:K], 1e-3, 1 - 1e-3))
    a_n = norm.ppf(np.clip(0.05 + 0.3 * u[K:2 * K], 1e-3, 1 - 1e-3))
    b = 0.1 + 0.5 * u[2 * K:3 * K]
    logit_pi = np.log(0.1 / 0.9) + u[-1] - 0.5

    def unpack(v):
        return v[:K], v[K:2 * K], v[2 * K:3 * K], 1 / (1 + np.exp(-v[-1]))

    def neg(v):
        aw, an, bb, pi = unpack(v)
        lw = _pattern_logp(pats, aw, bb, nodes, wts) + np.log(pi)
        ln = _pattern_logp(pats, an, bb, nodes, wts) + np.log1p(-pi)
        m = np.maximum(lw, ln)
        denom = m + np.log(np.exp(lw - m) + np.exp(ln - m))
        # weak ridge on loadings and intercepts far from 0 keeps the boundary
        # honest, mirroring D-034's Beta(2,2) in probit geometry
        pen = 1e-3 * (bb @ bb) + 1e-5 * (aw @ aw + an @ an)
        return -(counts * denom).sum() + pen * counts.sum() * 1e-6

    v0 = np.concatenate([a_w, a_n, b, [logit_pi]])
    res = minimize(neg, v0, method="L-BFGS-B",
                   options={"maxiter": 800, "ftol": 1e-12})
    aw, an, bb, pi = unpack(res.x)

    # orientation on the anchor's marginal fire rate (D-034)
    fire_w = float((norm.cdf(aw[anchor] + bb[anchor] * nodes) * wts).sum())
    fire_n = float((norm.cdf(an[anchor] + bb[anchor] * nodes) * wts).sum())
    if fire_n > fire_w:
        aw, an = an, aw
        pi = 1 - pi

    lw = _pattern_logp(pats, aw, bb, nodes, wts) + np.log(pi)
    ln = _pattern_logp(pats, an, bb, nodes, wts) + np.log1p(-pi)
    m = np.maximum(lw, ln)
    denom = m + np.log(np.exp(lw - m) + np.exp(ln - m))
    post = np.exp(lw - denom)
    loglik = float((counts * denom).sum())

    alpha = np.array([(norm.cdf(aw[k] + bb[k] * nodes) * wts).sum()
                      for k in range(K)])
    beta = 1 - np.array([(norm.cdf(an[k] + bb[k] * nodes) * wts).sum()
                         for k in range(K)])
    return {"pi": float(pi), "a_word": aw.tolist(), "a_non": an.tolist(),
            "loadings": bb.tolist(),
            "alpha_marginal": alpha.tolist(), "beta_marginal": beta.tolist(),
            "loglik": loglik, "converged": bool(res.success),
            "posterior_by_pattern": post.tolist()}
