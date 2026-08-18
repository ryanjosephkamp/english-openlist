"""
S4 and S5 — the feature-augmented specifications.

S4: two classes; the PRIOR becomes per-word, pi_i = sigmoid(w · x_i), so two
words with the same all-zero detector pattern but different orthotactics or
volume histories receive different posteriors — the first specification that
can say anything inside the 8.86M-word all-zero cell.

S5: three classes {WORD, OCR, NEITHER}; multinomial-logit prior over classes
from the same features; per-class detector fire probabilities. The OCR class
is the response to the frame-contamination finding (§2.4): it is oriented, per
D-034, as the class with the highest posterior-weighted mean of the typed-
confusion ratio, and WORD vs NEITHER is resolved by the wiktionary_english
anchor.

Implementation notes that matter for correctness:
  * The detector likelihood depends only on the pattern, so the E-step is a
    per-pattern table gathered to words (one fancy-index over 9.79M) plus the
    per-word prior — the M-step for detector rates re-collapses to patterns.
    An EM iteration is a few vectorised passes, ~1-2 s.
  * The prior weights update by weighted Newton (IRLS) inside each M-step —
    two Newton steps per EM iteration are enough; the EM envelope tolerates
    inexact M-steps.
  * Beta(2,2) MAP on all rates (D-034); L2 1e-6 on prior weights.
  * Multi-start honours §5.4's >= 50: fifty short sha256-seeded runs, the top
    three refined to convergence, all logliks reported.
"""

from __future__ import annotations

import numpy as np

from .em import BETA_A, BETA_B, seeded_uniform

RIDGE_W = 1e-6


def _sigmoid(z):
    return 1 / (1 + np.exp(-np.clip(z, -35, 35)))


def _pattern_class_loglik(pats, rates):
    """log P(pattern | class) for one class's fire-rate vector."""
    p = np.clip(rates, 1e-9, 1 - 1e-9)
    return pats @ np.log(p) + (1 - pats) @ np.log1p(-p)


def _softmax(Z):
    m = Z.max(axis=1, keepdims=True)
    e = np.exp(Z - m)
    return e / e.sum(axis=1, keepdims=True)


# ---------------------------------------------------------------------------
# S4
# ---------------------------------------------------------------------------

def fit_s4(pat_ids, pats, X, seed="s4", max_iter=60, tol=1e-7,
           newton_steps=2, anchor=1, w_init=None, rates_init=None):
    n, d = X.shape
    K = pats.shape[1]
    Xb = np.column_stack([np.ones(n, dtype=np.float32), X])

    u = seeded_uniform(seed, 2 * K + 1)
    alpha = 0.55 + 0.4 * u[:K]
    beta = 0.55 + 0.4 * u[K:2 * K]
    w = np.zeros(d + 1)
    w[0] = np.log(0.04 / 0.96) + (u[-1] - 0.5)
    if w_init is not None:
        w = w_init.copy()
    if rates_init is not None:
        alpha, beta = rates_init[0].copy(), rates_init[1].copy()

    prev = -np.inf
    for it in range(max_iter):
        la = _pattern_class_loglik(pats, alpha)          # [P]
        lb = _pattern_class_loglik(pats, 1 - beta)       # fire prob for nonword
        eta = Xb @ w                                     # [n]
        lw = la[pat_ids] + np.log(_sigmoid(eta))
        ln = lb[pat_ids] + np.log(_sigmoid(-eta))
        m = np.maximum(lw, ln)
        denom = m + np.log(np.exp(lw - m) + np.exp(ln - m))
        post = np.exp(lw - denom)                        # P(word | y, x)
        loglik = float(denom.sum())
        if abs(loglik - prev) < tol * max(1.0, abs(prev)):
            break
        prev = loglik

        # detector rates: collapse posteriors to patterns
        nw = np.bincount(pat_ids, weights=post, minlength=len(pats))
        nn = np.bincount(pat_ids, weights=1 - post, minlength=len(pats))
        Nw, Nn = nw.sum(), nn.sum()
        pf = pats.astype(np.float64)
        alpha = np.clip((nw @ pf + BETA_A - 1) / (Nw + BETA_A + BETA_B - 2),
                        1e-9, 1 - 1e-9)
        beta = np.clip((nn @ (1 - pf) + BETA_A - 1) / (Nn + BETA_A + BETA_B - 2),
                       1e-9, 1 - 1e-9)

        # prior weights: weighted logistic Newton on post ~ Xb
        for _ in range(newton_steps):
            mu = _sigmoid(Xb @ w)
            g = Xb.T @ (post - mu) - RIDGE_W * w * n
            s = np.maximum(mu * (1 - mu), 1e-6)
            H = (Xb * s[:, None]).T @ Xb + RIDGE_W * n * np.eye(d + 1)
            w = w + np.linalg.solve(H, g)

    # anchor orientation (D-034)
    if alpha[anchor] + beta[anchor] < 1:
        alpha, beta = 1 - beta, 1 - alpha
        w = -w
        la = _pattern_class_loglik(pats, alpha)
        lb = _pattern_class_loglik(pats, 1 - beta)
        eta = Xb @ w
        lw = la[pat_ids] + np.log(_sigmoid(eta))
        ln = lb[pat_ids] + np.log(_sigmoid(-eta))
        m = np.maximum(lw, ln)
        denom = m + np.log(np.exp(lw - m) + np.exp(ln - m))
        post = np.exp(lw - denom)
        loglik = float(denom.sum())

    return {"alpha": alpha.tolist(), "beta": beta.tolist(),
            "w": w.tolist(), "loglik": loglik, "iters": it + 1,
            "mean_prior": float(_sigmoid(Xb @ w).mean())}, post


# ---------------------------------------------------------------------------
# S5
# ---------------------------------------------------------------------------

def fit_s5(pat_ids, pats, X, ocr_col: int, seed="s5", max_iter=60, tol=1e-7,
           newton_steps=2, anchor=1, init=None):
    """Three classes: 0=WORD, 1=OCR, 2=NEITHER (post-orientation)."""
    n, d = X.shape
    K = pats.shape[1]
    C = 3
    Xb = np.column_stack([np.ones(n, dtype=np.float32), X])

    u = seeded_uniform(seed, C * K + 2 * (d + 1))
    rates = np.empty((C, K))
    rates[0] = 0.55 + 0.4 * u[:K]                  # word: fires
    rates[1] = 0.02 + 0.1 * u[K:2 * K]             # ocr: mostly silent
    rates[2] = 0.02 + 0.1 * u[2 * K:3 * K]         # neither: mostly silent
    W = np.zeros((C - 1, d + 1))                   # class 2 = reference
    W[0, 0] = np.log(0.05 / 0.90)
    W[1, 0] = np.log(0.05 / 0.90)
    if init is not None:
        rates, W = init[0].copy(), init[1].copy()

    prev = -np.inf
    for it in range(max_iter):
        L = np.stack([_pattern_class_loglik(pats, rates[c]) for c in range(C)])
        Z = np.zeros((n, C))
        Z[:, :2] = Xb @ W.T
        logprior = Z - _logsumexp_rows(Z)
        S = L[:, pat_ids].T + logprior                 # [n, C]
        m = S.max(axis=1, keepdims=True)
        denom = (m + np.log(np.exp(S - m).sum(axis=1, keepdims=True)))
        post = np.exp(S - denom)                       # [n, C]
        loglik = float(denom.sum())
        if abs(loglik - prev) < tol * max(1.0, abs(prev)):
            break
        prev = loglik

        pf = pats.astype(np.float64)
        for c in range(C):
            nc = np.bincount(pat_ids, weights=post[:, c], minlength=len(pats))
            Nc = nc.sum()
            rates[c] = np.clip((nc @ pf + BETA_A - 1)
                               / (Nc + BETA_A + BETA_B - 2), 1e-9, 1 - 1e-9)

        # multinomial logit Newton (block per non-reference class)
        for _ in range(newton_steps):
            Z = np.zeros((n, C)); Z[:, :2] = Xb @ W.T
            P = _softmax(Z)
            for c in range(2):
                g = Xb.T @ (post[:, c] - P[:, c]) - RIDGE_W * W[c] * n
                s = np.maximum(P[:, c] * (1 - P[:, c]), 1e-6)
                H = (Xb * s[:, None]).T @ Xb + RIDGE_W * n * np.eye(d + 1)
                W[c] = W[c] + np.linalg.solve(H, g)

    # ---- orientation, D-034: OCR = highest mean typed-confusion ratio;
    # WORD vs NEITHER by the anchor detector's fire rate ------------------
    ocr_means = [(post[:, c] @ X[:, ocr_col]) / max(post[:, c].sum(), 1e-9)
                 for c in range(C)]
    ocr_class = int(np.argmax(ocr_means))
    rest = [c for c in range(C) if c != ocr_class]
    word_class = rest[int(np.argmax([rates[c][anchor] for c in rest]))]
    neither = [c for c in range(C) if c not in (ocr_class, word_class)][0]
    order = [word_class, ocr_class, neither]
    rates = rates[order]
    post = post[:, order]
    # re-derive W for the new ordering by one Newton pass against posteriors
    W = np.zeros((2, Xb.shape[1]))
    for _ in range(8):
        Z = np.zeros((n, C)); Z[:, :2] = Xb @ W.T
        P = _softmax(Z)
        for c in range(2):
            g = Xb.T @ (post[:, c] - P[:, c]) - RIDGE_W * W[c] * n
            s = np.maximum(P[:, c] * (1 - P[:, c]), 1e-6)
            H = (Xb * s[:, None]).T @ Xb + RIDGE_W * n * np.eye(Xb.shape[1])
            W[c] = W[c] + np.linalg.solve(H, g)

    return {"rates_word": rates[0].tolist(), "rates_ocr": rates[1].tolist(),
            "rates_neither": rates[2].tolist(), "W": W.tolist(),
            "loglik": loglik, "iters": it + 1,
            "class_mass": post.sum(axis=0).tolist(),
            "ocr_feature_means": [float(x) for x in
                                  [ocr_means[c] for c in order]]}, post


def _logsumexp_rows(Z):
    m = Z.max(axis=1, keepdims=True)
    return m + np.log(np.exp(Z - m).sum(axis=1, keepdims=True))
