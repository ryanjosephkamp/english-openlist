"""
S1 — classic Dawid–Skene, two classes, conditional independence, MAP-EM.

Fitted over the collapsed pattern table, so an EM iteration is a few hundred
multiplications and the whole fit is milliseconds — which is what makes the
50-start battery and the profile likelihoods affordable rather than heroic.

MAP with Beta(a, b) priors on every rate (D-034): a source that behaves
near-perfectly in the observed table would otherwise drive a rate to 1.0,
the information matrix goes singular, and §5.2 becomes undefined. The prior
counts enter the M-step as pseudo-observations, nothing more exotic.

Everything is deterministic: initial parameters come from sha256-seeded
uniforms, and the same seed reproduces the same trajectory bit-for-bit.
"""

from __future__ import annotations

import hashlib

import numpy as np

BETA_A, BETA_B = 2.0, 2.0     # D-034 boundary priors


def seeded_uniform(seed: str, n: int) -> np.ndarray:
    """n uniforms in (0,1) from sha256(seed:i) — the project's determinism
    rule, no library RNG."""
    out = np.empty(n)
    for i in range(n):
        h = hashlib.sha256(f"{seed}:{i}".encode()).digest()
        out[i] = (int.from_bytes(h[:8], "big") + 0.5) / 2**64
    return out


def init_params(seed: str, K: int):
    u = seeded_uniform(seed, 2 * K + 1)
    pi = 0.05 + 0.4 * u[0]                 # prevalence somewhere plausible
    alpha = 0.55 + 0.4 * u[1:K + 1]        # word class fires more...
    beta = 0.55 + 0.4 * u[K + 1:]          # ...nonword class stays silent
    return pi, alpha, beta


def pattern_loglik(pats, alpha, beta):
    """log P(pattern | class) for both classes; pats [P,K] uint8."""
    pats = pats.astype(np.float64)
    la = pats @ np.log(alpha) + (1 - pats) @ np.log1p(-alpha)
    lb = pats @ np.log1p(-beta) + (1 - pats) @ np.log(beta)
    return la, lb        # word class, nonword class


def e_step(pats, counts, pi, alpha, beta):
    la, lb = pattern_loglik(pats, alpha, beta)
    lw = np.log(pi) + la
    ln = np.log1p(-pi) + lb
    m = np.maximum(lw, ln)
    denom = m + np.log(np.exp(lw - m) + np.exp(ln - m))
    post = np.exp(lw - denom)                       # P(word | pattern)
    loglik = float((counts * denom).sum())
    return post, loglik


def m_step(pats, counts, post):
    pats = pats.astype(np.float64)
    nw = counts * post
    nn = counts * (1 - post)
    Nw, Nn = nw.sum(), nn.sum()
    pi = Nw / (Nw + Nn)
    alpha = (nw @ pats + (BETA_A - 1)) / (Nw + BETA_A + BETA_B - 2)
    beta = (nn @ (1 - pats) + (BETA_A - 1)) / (Nn + BETA_A + BETA_B - 2)
    eps = 1e-9
    return pi, np.clip(alpha, eps, 1 - eps), np.clip(beta, eps, 1 - eps)


def log_prior(pi, alpha, beta):
    return float(((BETA_A - 1) * (np.log(alpha) + np.log(beta))
                  + (BETA_B - 1) * (np.log1p(-alpha) + np.log1p(-beta))).sum())


def fit_s1(pats, counts, seed: str = "s1", max_iter: int = 500,
           tol: float = 1e-9, anchor: int | None = None):
    """Returns dict with pi, alpha, beta, loglik (data), logpost, iters.
    `anchor`: detector index whose alpha+beta>1 orients the classes (D-034);
    if the converged fit violates it, the labelling is swapped."""
    pi, alpha, beta = init_params(seed, pats.shape[1])
    prev = -np.inf
    for it in range(max_iter):
        post, loglik = e_step(pats, counts, pi, alpha, beta)
        pi, alpha, beta = m_step(pats, counts, post)
        obj = loglik + log_prior(pi, alpha, beta)
        if abs(obj - prev) < tol * max(1.0, abs(prev)):
            break
        prev = obj
    if anchor is not None and alpha[anchor] + beta[anchor] < 1:
        # relabel: swap classes
        pi = 1 - pi
        alpha, beta = 1 - beta, 1 - alpha
        post, loglik = e_step(pats, counts, pi, alpha, beta)
    post, loglik = e_step(pats, counts, pi, alpha, beta)
    return {"pi": float(pi), "alpha": alpha.tolist(), "beta": beta.tolist(),
            "loglik": loglik, "logpost": loglik + log_prior(pi, alpha, beta),
            "iters": it + 1, "posterior_by_pattern": post.tolist()}
