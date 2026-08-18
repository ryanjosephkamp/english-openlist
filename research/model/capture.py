"""
The capture-recapture population estimate — how many real words no source
caught.

Estimand and route: within the fitted WORD class, the detector model gives
P0_W = P(all detectors silent | word). The class-W words the sources DID
catch number N_caught_W = sum over nonzero patterns of count x P(word |
pattern). If capture were homogeneous within the class, the total would be

    N_W_total = N_caught_W / (1 - P0_W)

and the words no source caught = N_W_total - N_caught_W. That subsumes both
the frame's own all-zero cell and words outside the frame entirely — the
model cannot tell those apart, and does not pretend to.

THE CAVEAT IS PART OF THE NUMBER (PROTOCOL §4): capture probability within
the word class is heterogeneous — rare technical vocabulary is systematically
less catchable than core vocabulary — and heterogeneity biases this estimator
DOWNWARD. The figure is therefore a LOWER BOUND on English vocabulary under
the operational definition, stated as such everywhere it appears, and the
independent literature on Zipfian capture (Efron & Thisted onward) says the
underestimate can be large.

Computed from S1, the only pattern specification that survived SR5 — S2,
whose interaction terms would refine P0_W, was excluded by its own gate
(D-035), and using its lambdas anyway would be exactly the post-hoc rescue
the decision log forbids.
"""

from __future__ import annotations

import numpy as np

from .data import enumerate_cells
from .em import pattern_loglik


def population_estimate(fit, pats, counts):
    alpha = np.array(fit["alpha"])
    pi = fit["pi"]
    post = np.array(fit["posterior_by_pattern"])

    nonzero = pats.sum(axis=1) > 0
    n_caught = float((counts[nonzero] * post[nonzero]).sum())

    p0_w = float(np.exp(np.log1p(-alpha).sum()))     # all silent | word
    n_total = n_caught / (1 - p0_w)
    uncaught = n_total - n_caught

    # words the model places in the frame's all-zero cell
    az = np.flatnonzero(~nonzero)
    in_frame_az = float((counts[az] * post[az]).sum()) if len(az) else 0.0

    return {
        "estimator": "class-W homogeneous-capture extrapolation from S1",
        "P0_word_all_silent": p0_w,
        "caught_words_expected": n_caught,
        "total_words_lower_bound": n_total,
        "uncaught_words_lower_bound": uncaught,
        "of_which_model_places_in_frame_allzero": in_frame_az,
        "caveat": ("heterogeneous capture biases this DOWNWARD; report only "
                   "as a lower bound on vocabulary under the operational "
                   "definition (PROTOCOL §4)"),
    }
