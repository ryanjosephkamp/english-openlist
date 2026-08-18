"""
Phase 3's invariants: EM correctness on knowns, exact normalization, anchor
relabelling, quadrature against closed form, and sha256 determinism.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.model.data import enumerate_cells  # noqa: E402
from research.model.em import e_step, fit_s1, pattern_loglik  # noqa: E402
from research.model.loglinear import S2Model  # noqa: E402
from research.model.randeff import _pattern_logp, _quad  # noqa: E402


def synth_s1(K=6, N=1_000_000):
    pi = 0.3
    a = np.array([.9, .8, .85, .7, .95, .75])
    b = np.array([.97, .9, .92, .88, .99, .85])
    cells = enumerate_cells(K)
    la, lb = pattern_loglik(cells, a, b)
    p = pi * np.exp(la) + (1 - pi) * np.exp(lb)
    counts = np.round(p * N).astype(np.int64)
    return cells, counts, pi, a, b


class TestS1:
    def test_mixture_normalizes(self):
        cells, counts, pi, a, b = synth_s1()
        la, lb = pattern_loglik(cells, a, b)
        assert abs((pi * np.exp(la) + (1 - pi) * np.exp(lb)).sum() - 1) < 1e-12

    def test_recovers_known_world(self):
        cells, counts, pi, a, b = synth_s1()
        fit = fit_s1(cells, counts, seed="t", anchor=0)
        assert abs(fit["pi"] - pi) < 0.01
        assert np.max(np.abs(np.array(fit["alpha"]) - a)) < 0.01
        assert np.max(np.abs(np.array(fit["beta"]) - b)) < 0.01

    def test_deterministic(self):
        cells, counts, *_ = synth_s1()
        f1 = fit_s1(cells, counts, seed="t", anchor=0)
        f2 = fit_s1(cells, counts, seed="t", anchor=0)
        assert f1["alpha"] == f2["alpha"] and f1["logpost"] == f2["logpost"]

    def test_anchor_orients_a_flipped_start(self):
        """A seed that converges to the mirrored labelling must come back
        oriented: anchor detector's alpha + beta > 1."""
        cells, counts, *_ = synth_s1()
        for s in range(6):
            fit = fit_s1(cells, counts, seed=f"flip{s}", anchor=0)
            assert fit["alpha"][0] + fit["beta"][0] > 1

    def test_posterior_monotone_in_evidence(self):
        cells, counts, pi, a, b = synth_s1()
        fit = fit_s1(cells, counts, seed="t", anchor=0)
        post, _ = e_step(cells, counts, fit["pi"],
                         np.array(fit["alpha"]), np.array(fit["beta"]))
        all_zero = int(np.flatnonzero(cells.sum(1) == 0)[0])
        all_one = int(np.flatnonzero(cells.sum(1) == cells.shape[1])[0])
        assert post[all_one] > 0.99 and post[all_zero] < 0.05


class TestS2:
    def test_class_distribution_sums_to_one(self):
        m = S2Model(5, [(0, 1), (2, 3)])
        lp = m.class_logp(np.array([.5, -.2, 1., 0., -.5]),
                          np.array([.7, -.3]))
        assert abs(np.exp(lp).sum() - 1) < 1e-12

    def test_zero_lambda_reduces_to_independence(self):
        m = S2Model(4, [(0, 1)])
        theta = np.array([0.3, -0.7, 1.1, -0.2])
        lp = m.class_logp(theta, np.zeros(1))
        p = 1 / (1 + np.exp(-theta))
        cells = enumerate_cells(4)
        indep = (cells * np.log(p) + (1 - cells) * np.log(1 - p)).sum(1)
        assert np.allclose(lp, indep, atol=1e-10)


class TestS3Quadrature:
    def test_matches_closed_form_at_zero_loading(self):
        from scipy.stats import norm
        nodes, wts = _quad()
        pats = enumerate_cells(4)
        a = np.array([0.5, -0.3, 1.0, -1.2])
        lp = _pattern_logp(pats, a, np.zeros(4), nodes, wts)
        p1 = norm.cdf(a)
        closed = (pats * np.log(p1) + (1 - pats) * np.log(1 - p1)).sum(1)
        assert np.allclose(lp, closed, atol=1e-10)

    def test_marginal_sums_to_one_with_loading(self):
        nodes, wts = _quad()
        pats = enumerate_cells(5)
        lp = _pattern_logp(pats, np.array([.2, -.5, .9, 0., -1.]),
                           np.array([.8, .3, 1.2, .5, .9]), nodes, wts)
        assert abs(np.exp(lp).sum() - 1) < 1e-9
