"""
The typed OCR-confusion channel — D-012's discriminating feature.

Raw edit distance was tested in Phase 0 and rejected: real words cluster near
other real words through inflection, so proximity alone scored HIGHER on a
control of ordinary valid words (50.5%) than on the suspect strata. What
discriminates is the TYPED, DIRECTIONAL confusion — `schoolmaster` was scanned
as `schoolinaster` because metal-type `m` reads as `in`, not because the two
strings are generically close.

The six pairs are exactly D-012's, source-glyph -> artifact-glyph:

    m -> in     rn -> m     l -> i     e -> c     c -> e     li -> h

Two directions, two uses:

  * detection (artifact?): in a candidate, substitute artifact-glyphs BACK to
    source-glyphs, one site at a time; a hit in the reference lexicon plus a
    large frequency gap is the artifact signature.
  * generation (controls): corrupt known-real words source->artifact to
    manufacture the OCR negative-control family (§6.3), which is SR3's
    instrument.

Reference lexicon: WordNet ∪ web2 — deliberately not the frame's own valid
labels (circularity) and not the full detector union (an artifact of a rare
SOWPODS word should still read as an artifact).
"""

from __future__ import annotations

#: (source_glyph, artifact_glyph) — the scan turns source into artifact.
CONFUSIONS = [
    ("m", "in"),
    ("rn", "m"),
    ("l", "i"),
    ("e", "c"),
    ("c", "e"),
    ("li", "h"),
]


def detect_neighbors(word: str, reference: set[str]):
    """Yield (source_word, pair) for every single-site back-substitution of an
    artifact glyph that lands in the reference lexicon."""
    seen = set()
    for src, art in CONFUSIONS:
        start = 0
        while True:
            i = word.find(art, start)
            if i < 0:
                break
            cand = word[:i] + src + word[i + len(art):]
            if cand != word and cand in reference and cand not in seen:
                seen.add(cand)
                yield cand, (src, art)
            start = i + 1


def corrupt(word: str, site_unit: float):
    """Generate ONE corruption of a real word, source->artifact, choosing the
    site by a supplied uniform variate so control decks stay deterministic.
    Returns None when the word offers no confusion site."""
    sites = []
    for src, art in CONFUSIONS:
        start = 0
        while True:
            i = word.find(src, start)
            if i < 0:
                break
            sites.append((i, src, art))
            start = i + 1
    if not sites:
        return None
    i, src, art = sites[int(site_unit * len(sites)) % len(sites)]
    return word[:i] + art + word[i + len(src):]
