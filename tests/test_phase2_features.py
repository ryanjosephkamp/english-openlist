"""
Phase 2's invariants: leakage-clean partitions, honest probabilities, and the
typed OCR channel doing what D-012 measured it must.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research.features.charmodel import ALPHABET, BOUNDARY, CharModel  # noqa: E402
from research.features.ocr import corrupt, detect_neighbors  # noqa: E402
from research.features.partitions import assign, hash_unit  # noqa: E402
from research.features.productivity import parse_suffix  # noqa: E402


class TestPartitions:
    def test_deterministic(self):
        assert assign("blameworthy") == assign("blameworthy")
        assert 0.0 <= hash_unit("anything") < 1.0

    def test_membership_is_per_word(self):
        """Hash-range assignment: one word's partition never depends on what
        else is in the pool — the leakage guarantee's foundation."""
        a1 = {w: assign(w) for w in ("cat", "dog", "bird")}
        a2 = {w: assign(w) for w in ("cat", "dog", "bird", "axolotl", "newt")}
        for w in a1:
            assert a1[w] == a2[w]

    def test_all_three_partitions_reachable(self):
        seen = {assign(f"w{i}") for i in range(2000)}
        assert seen == {"train", "dev", "test"}


class TestCharModel:
    def _model(self):
        m = CharModel(order=3)
        m.fit(["cat", "cats", "mat", "mats", "rat", "rats"])
        m.finalize()
        m.tune(["bat", "bats"])
        return m

    def test_distributions_sum_to_one(self):
        m = self._model()
        for h in (BOUNDARY * 2, "ca", "at", "zz"):
            assert abs(sum(m.prob(h, c) for c in ALPHABET) - 1.0) < 1e-9

    def test_trained_shapes_beat_junk(self):
        m = self._model()
        assert m.logp_word("cat")[1] > m.logp_word("xqz")[1]

    def test_finalize_matches_unfinalized(self):
        a = CharModel(order=3)
        a.fit(["cat", "cats", "mat"])
        b = CharModel(order=3)
        b.fit(["cat", "cats", "mat"])
        b.finalize()
        for h, c in ((BOUNDARY * 2, "c"), ("ca", "t"), ("at", "$")):
            assert abs(a.prob(h, c) - b.prob(h, c)) < 1e-12

    def test_sampling_is_deterministic(self):
        m = self._model()
        def units():
            x = 0.123456
            while True:
                yield x
                x = (x * 7919.0) % 1.0
        w1 = m.sample_word(units())
        w2 = m.sample_word(units())
        assert w1 == w2


class TestOCR:
    REF = {"schoolmaster", "modern", "clean"}

    def test_the_canonical_case(self):
        hits = dict(detect_neighbors("schoolinaster", self.REF))
        assert "schoolmaster" in hits and hits["schoolmaster"] == ("m", "in")

    def test_direction_matters(self):
        # schoolmaster itself is NOT one artifact-step from anything here
        assert not list(detect_neighbors("schoolmaster", self.REF))

    def test_corrupt_then_detect_round_trip(self):
        c = corrupt("modern", 0.99)
        assert c is not None and c != "modern"
        assert any(src == "modern" for src, _ in detect_neighbors(c, self.REF))

    def test_no_site_returns_none(self):
        assert corrupt("dog", 0.5) is None


class TestProductivity:
    REF = {"happy", "run", "bake", "sing"}

    def test_orthographic_restorations(self):
        assert parse_suffix("happiness", self.REF) == ("ness", "happy")
        assert parse_suffix("running", self.REF) == ("ing", "run")
        assert parse_suffix("baking", self.REF) == ("ing", "bake")

    def test_unattested_stem_refuses(self):
        assert parse_suffix("zzzqings", self.REF) is None
