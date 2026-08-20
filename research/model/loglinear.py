"""
S2 — latent class with declared within-class interactions (Espeland &
Handelman's family).

Per class c, the detector vector follows an exponential-family model

    P(y | c) ∝ exp( θ_c · y  +  Σ_{(j,k) ∈ E} λ_c,jk · y_j y_k )

with E the NINE edges declared in the manifest (D-002/§2.3) — nothing else.
K = 12 means the normalizer is an exact sum over 4,096 cells, so there is no
approximation anywhere in this model: the E-step, the M-step gradients and
the reported loglik are all exact.

Fitting: EM in the latent class; the M-step maximizes each class's weighted
log-linear likelihood by Newton steps on the exact gradient/Hessian-free
L-BFGS (scipy), warm-started from the previous iteration. The main-effect
Beta(2,2) boundary logic from S1 appears here as a quadratic penalty on
natural parameters (equivalent regularisation in the exponential-family
geometry), declared once: ridge 1e-4 on λ, none needed on θ beyond the
penalty implied by finite cells.

Orientation (D-034): after convergence, the class with the higher marginal
fire rate for the anchor detector (wiktionary_english) is WORD.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from .em import seeded_uniform
from .data import enumerate_cells

RIDGE_LAMBDA = 1e-4


class S2Model:
    def __init__(self, K: int, edges: list[tuple[int, int]]):
        self.K = K
        self.edges = edges
        self.cells = enumerate_cells(K).astype(np.float64)          # [4096,K]
        self.cell_pairs = np.stack([self.cells[:, j] * self.cells[:, k]
                                    for j, k in edges], axis=1)     # [4096,E]

    def class_logp(self, theta, lam):
        """log P(cell | class) for all 4096 cells, exactly normalized."""
        s = self.cells @ theta + self.cell_pairs @ lam
        m = s.max()
        logZ = m + np.log(np.exp(s - m).sum())
        return s - logZ

    def _pack(self, theta_w, lam_w, theta_n, lam_n, pi):
        return np.concatenate([theta_w, lam_w, theta_n, lam_n,
                               [np.log(pi / (1 - pi))]])

    def _unpack(self, v):
        K, E = self.K, len(self.edges)
        i = 0
        theta_w = v[i:i + K]; i += K
        lam_w = v[i:i + E]; i += E
        theta_n = v[i:i + K]; i += K
        lam_n = v[i:i + E]; i += E
        pi = 1 / (1 + np.exp(-v[i]))
        return theta_w, lam_w, theta_n, lam_n, pi

    def fit(self, pats, counts, seed: str = "s2", max_em: int = 200,
            tol: float = 1e-8, anchor: int = 1):
        K, E = self.K, len(self.edges)
        u = seeded_uniform(seed, 2 * (K + E) + 1)
        theta_w = 1.0 + u[:K]                    # word class fires more
        lam_w = 0.2 * (u[K:K + E] - .5)
        theta_n = -3.0 - u[K + E:2 * K + E]
        lam_n = 0.2 * (u[2 * K + E:2 * (K + E)] - .5)
        pi = 0.03 + 0.1 * u[-1]

        # map observed patterns to cell indices for the E-step
        weights = (1 << np.arange(K)).astype(np.int64)
        obs_idx = (pats.astype(np.int64) @ weights)

        pats_f = pats.astype(np.float64)
        obs_pairs = np.stack([pats_f[:, j] * pats_f[:, k]
                              for j, k in self.edges], axis=1)

        prev = -np.inf
        for it in range(max_em):
            lw = self.class_logp(theta_w, lam_w)[obs_idx] + np.log(pi)
            ln = self.class_logp(theta_n, lam_n)[obs_idx] + np.log1p(-pi)
            m = np.maximum(lw, ln)
            denom = m + np.log(np.exp(lw - m) + np.exp(ln - m))
            post = np.exp(lw - denom)
            loglik = float((counts * denom).sum())
            if abs(loglik - prev) < tol * max(1.0, abs(prev)):
                break
            prev = loglik

            nw = counts * post
            nn = counts * (1 - post)
            pi = nw.sum() / counts.sum()

            for (n_c, ref) in ((nw, "w"), (nn, "n")):
                suff_y = n_c @ pats_f          # observed sufficient stats
                suff_p = n_c @ obs_pairs
                N_c = n_c.sum()

                def neg(v, suff_y=suff_y, suff_p=suff_p, N_c=N_c):
                    th, la_ = v[:K], v[K:]
                    s = self.cells @ th + self.cell_pairs @ la_
                    mm = s.max()
                    logZ = mm + np.log(np.exp(s - mm).sum())
                    val = -(suff_y @ th + suff_p @ la_ - N_c * logZ) \
                          + RIDGE_LAMBDA * (la_ @ la_) * N_c
                    p = np.exp(s - logZ)
                    g_th = -(suff_y - N_c * (p @ self.cells))
                    g_la = -(suff_p - N_c * (p @ self.cell_pairs)) \
                           + 2 * RIDGE_LAMBDA * la_ * N_c
                    return val, np.concatenate([g_th, g_la])

                x0 = (np.concatenate([theta_w, lam_w]) if ref == "w"
                      else np.concatenate([theta_n, lam_n]))
                res = minimize(neg, x0, jac=True, method="L-BFGS-B",
                               options={"maxiter": 60, "ftol": 1e-12})
                if ref == "w":
                    theta_w, lam_w = res.x[:K], res.x[K:]
                else:
                    theta_n, lam_n = res.x[:K], res.x[K:]

        # orientation: WORD is the class where the anchor fires more
        pw = np.exp(self.class_logp(theta_w, lam_w))
        pn = np.exp(self.class_logp(theta_n, lam_n))
        fire_w = float((pw * self.cells[:, anchor]).sum())
        fire_n = float((pn * self.cells[:, anchor]).sum())
        if fire_n > fire_w:
            theta_w, theta_n = theta_n, theta_w
            lam_w, lam_n = lam_n, lam_w
            pi = 1 - pi
            lw = self.class_logp(theta_w, lam_w)[obs_idx] + np.log(pi)
            ln = self.class_logp(theta_n, lam_n)[obs_idx] + np.log1p(-pi)
            m = np.maximum(lw, ln)
            denom = m + np.log(np.exp(lw - m) + np.exp(ln - m))
            post = np.exp(lw - denom)
            loglik = float((counts * denom).sum())

        # implied marginal fire rates per class, for comparability with S1
        alpha = (pw * self.cells.T).sum(axis=1) if fire_w >= fire_n else \
                (np.exp(self.class_logp(theta_w, lam_w)) * self.cells.T).sum(axis=1)
        pw = np.exp(self.class_logp(theta_w, lam_w))
        pn = np.exp(self.class_logp(theta_n, lam_n))
        alpha = (pw[:, None] * self.cells).sum(axis=0)
        beta = 1 - (pn[:, None] * self.cells).sum(axis=0)

        return {"pi": float(pi),
                "theta_word": theta_w.tolist(), "lambda_word": lam_w.tolist(),
                "theta_non": theta_n.tolist(), "lambda_non": lam_n.tolist(),
                "alpha_marginal": alpha.tolist(),
                "beta_marginal": beta.tolist(),
                "loglik": loglik, "iters": it + 1,
                "posterior_by_pattern": post.tolist()}
