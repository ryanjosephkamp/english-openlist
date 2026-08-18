"""
The orthotactic channel: an interpolated character n-gram model.

P(c | h) = sum_k  lam_k * ML_k(c | h_k)   over orders k = 0..ORDER

with ML_0 the uniform distribution over the 27-symbol alphabet (a-z plus the
boundary marker) and the lambdas tuned on the dev partition by expectation
maximisation. An interpolated model rather than stupid backoff because the
Phase 2 gate is held-out PERPLEXITY, which needs honest probabilities that sum
to one — a score that is not a distribution cannot be gated on.

Trained on TYPES, each word once: orthotactics is about which strings look
like English, and a token-weighted model would mostly learn the spelling of
`the`. The model never sees anything outside the train partition (§3.3); the
features manifest records the seed, the pool rule and the counts.

n-gram order 4 (three characters of history). Chosen, not tuned-by-test: the
dev EM picks the interpolation weights, and if high orders earn nothing the
lambdas simply collapse onto the lower orders — visible in the manifest rather
than silently absorbed.
"""

from __future__ import annotations

import math
from collections import defaultdict

BOUNDARY = "^"          # start-of-word history padding
END = "$"               # end-of-word event — length has to be a probability too
ALPHABET = [chr(c) for c in range(ord("a"), ord("z") + 1)] + [END]
ORDER = 4               # conditioning on up to ORDER-1 characters


class CharModel:
    def __init__(self, order: int = ORDER):
        self.order = order
        # counts[k] maps history (length k) -> {next_char: count}
        self.counts = [defaultdict(lambda: defaultdict(int)) for _ in range(order)]
        self.lambdas = [1.0 / (order + 1)] * (order + 1)  # + uniform floor
        self.uniform = 1.0 / len(ALPHABET)

    # -- training ------------------------------------------------------------

    def fit(self, words) -> None:
        for w in words:
            padded = BOUNDARY * (self.order - 1) + w + END
            for i in range(self.order - 1, len(padded)):
                c = padded[i]
                for k in range(self.order):
                    h = padded[i - k:i]
                    self.counts[k][h][c] += 1

    def finalize(self) -> None:
        """Freeze counts into probability tables. Summing a history's counts
        on every lookup is O(alphabet) per call; scoring ten million words
        makes that the whole runtime, so it happens once, here."""
        self._p = []
        for k in range(self.order):
            table = {}
            for h, dist in self.counts[k].items():
                total = sum(dist.values())
                table[h] = {c: n / total for c, n in dist.items()}
            self._p.append(table)

    def _ml(self, k: int, h: str, c: str) -> float:
        if hasattr(self, "_p"):
            dist = self._p[k].get(h)
            return dist.get(c, 0.0) if dist else 0.0
        dist = self.counts[k].get(h)
        if not dist:
            return 0.0
        total = sum(dist.values())
        return dist.get(c, 0) / total

    def _seen(self, k: int, h: str) -> bool:
        if hasattr(self, "_p"):
            return h in self._p[k]
        return h in self.counts[k]

    def prob(self, h: str, c: str) -> float:
        """P(c | h) under the interpolation, renormalized over the orders
        whose history was actually observed.

        Without the renormalization an UNSEEN history h_k contributes zero for
        every character, and that order's lambda mass simply vanishes — the
        "distribution" for junk-adjacent histories summed to 0.53 in the test
        that caught this. Dividing by the available lambda mass restores a
        proper distribution for every history, seen or not."""
        p = self.lambdas[0] * self.uniform
        mass = self.lambdas[0]
        for k in range(self.order):
            hk = h[len(h) - k:] if k else ""
            if self._seen(k, hk):
                mass += self.lambdas[k + 1]
                p += self.lambdas[k + 1] * self._ml(k, hk, c)
        return p / mass

    # -- EM for the interpolation weights, on dev ---------------------------

    def tune(self, dev_words, iterations: int = 12) -> list[float]:
        events = []
        for w in dev_words:
            padded = BOUNDARY * (self.order - 1) + w + END
            for i in range(self.order - 1, len(padded)):
                events.append((padded[max(0, i - self.order + 1):i], padded[i]))
        for _ in range(iterations):
            weight = [0.0] * (self.order + 1)
            for h, c in events:
                parts = [self.lambdas[0] * self.uniform]
                for k in range(self.order):
                    hk = h[len(h) - k:] if k else ""
                    if self._seen(k, hk):
                        parts.append(self.lambdas[k + 1] * self._ml(k, hk, c))
                    else:
                        parts.append(0.0)
                z = sum(parts)
                if z <= 0:
                    continue
                for j, part in enumerate(parts):
                    weight[j] += part / z
            total = sum(weight)
            self.lambdas = [x / total for x in weight]
        return self.lambdas

    # -- scoring -------------------------------------------------------------

    def logp_word(self, w: str) -> tuple[float, float]:
        """(total log10 P(word), per-character mean) including the END event."""
        padded = BOUNDARY * (self.order - 1) + w + END
        lp = 0.0
        n = 0
        for i in range(self.order - 1, len(padded)):
            h = padded[max(0, i - self.order + 1):i]
            p = self.prob(h, padded[i])
            lp += math.log10(max(p, 1e-12))
            n += 1
        return lp, lp / n

    def perplexity(self, words) -> float:
        """Held-out per-character perplexity, END events included."""
        total_lp, total_n = 0.0, 0
        for w in words:
            lp, _ = self.logp_word(w)
            total_lp += lp
            total_n += len(w) + 1
        return 10 ** (-total_lp / total_n)

    # -- sampling (for the pseudo-word negative controls) --------------------

    def sample_word(self, unit_stream, max_len: int = 24) -> str:
        """Draw one word using an iterator of uniform [0,1) variates — the
        caller supplies hash-derived units so sampling stays deterministic."""
        h = BOUNDARY * (self.order - 1)
        out = []
        while len(out) < max_len:
            u = next(unit_stream)
            acc = 0.0
            for c in ALPHABET:
                acc += self.prob(h, c)
                if u <= acc:
                    break
            if c == END:
                break
            out.append(c)
            h = (h + c)[-(self.order - 1):]
        return "".join(out)
