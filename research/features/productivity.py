"""
Morphological productivity — Baayen's P per affix, on the Google Books
aggregates.

Baayen's P = n1 / N: hapax types over total tokens for the morphological
category. The instrument PROTOCOL §3.2 names for the synthetic-intake
question — not "does MW list `advertings`" but "how productive is -ings on
gerund stems, measured".

One honest limitation, measured rather than assumed and recorded in the
features manifest: the 2020 Google Books release ships nothing below a floor
of 40 — on match_count AND on volume_count (both minima measured at exactly
40). Hapaxes therefore do not exist in this corpus under ANY definition:
n1(match==1) = 0 and n1(volume==1) = 0 for every affix, identically. Baayen's
potential productivity P = n1/N is NOT COMPUTABLE here, and pretending
otherwise produced a constant-zero feature that the gate caught at AUC 0.500
exactly.

What the corpus does support is REALIZED productivity, V/N — distinct types
per token of the affix category (Baayen 1993's type-count measures). It is a
different quantity with a lower theoretical ceiling: it measures how much of
the affix's yield is already attested, not the rate of new coinage. Both
hapax columns still ship (as zeros) so the censoring is visible in the table
itself, beside min_match_seen = 40.

An affix's category membership is string-match PLUS stem attestation in the
reference lexicon (WordNet ∪ web2): `-ings` on `deentrainings` counts only if
`deentrain`-ish stems resolve. Pure string-matching would count `sings` as
`s+ings`. Stem resolution tries the concatenative stem and standard
e-restoration / consonant-undoubling / y-restoration variants.
"""

from __future__ import annotations

SUFFIXES = [
    "s", "es", "ed", "ing", "ings", "er", "ers", "est", "ly", "ness",
    "nesses", "ish", "able", "ible", "ation", "ations", "ize", "ise",
    "ized", "ised", "izes", "ises", "izing", "ising", "ic", "al", "ous",
    "ment", "ments", "ity", "ities", "less", "ful", "dom", "hood", "ship",
    "like", "oses", "osis", "ette", "ism", "isms", "ist", "ists",
]
PREFIXES = [
    "un", "non", "re", "de", "anti", "pre", "over", "under", "out",
    "micro", "pseudo", "quasi", "super", "sub", "inter", "intra", "multi",
]
MIN_STEM = 3


def stem_variants(stem: str):
    """The concatenative stem plus the standard orthographic restorations."""
    yield stem
    yield stem + "e"                      # bak(ing) -> bake
    if len(stem) >= 2 and stem[-1] == stem[-2]:
        yield stem[:-1]                   # runn(ing) -> run
    if stem.endswith("i"):
        yield stem[:-1] + "y"             # happi(ness) -> happy


def parse_suffix(word: str, reference: set[str]):
    """Longest attested-stem suffix parse, or None."""
    for suf in sorted(SUFFIXES, key=len, reverse=True):
        if word.endswith(suf) and len(word) - len(suf) >= MIN_STEM:
            stem = word[: len(word) - len(suf)]
            for v in stem_variants(stem):
                if v in reference:
                    return suf, v
    return None


def parse_prefix(word: str, reference: set[str]):
    for pre in sorted(PREFIXES, key=len, reverse=True):
        if word.startswith(pre) and len(word) - len(pre) >= MIN_STEM:
            rest = word[len(pre):]
            if rest in reference:
                return pre, rest
    return None


def affix_table(gb_words, gb_match, gb_volume, reference: set[str]) -> dict:
    """
    One pass over the aggregate: per affix, token total N, type count V,
    volume-hapax count n1_vol, match-count-minimum (to show the floor), and
    P_vol = n1_vol / N.
    """
    stats = {("suffix", s): [0, 0, 0, float("inf")] for s in SUFFIXES}
    stats.update({("prefix", p): [0, 0, 0, float("inf")] for p in PREFIXES})
    for w, tm, tv in zip(gb_words, gb_match, gb_volume):
        ps = parse_suffix(w, reference)
        if ps:
            row = stats[("suffix", ps[0])]
            row[0] += int(tm)
            row[1] += 1
            if tv == 1:
                row[2] += 1
            if tm < row[3]:
                row[3] = tm
        pp = parse_prefix(w, reference)
        if pp:
            row = stats[("prefix", pp[0])]
            row[0] += int(tm)
            row[1] += 1
            if tv == 1:
                row[2] += 1
            if tm < row[3]:
                row[3] = tm
    out = {}
    for key, (N, V, n1_vol, min_match) in stats.items():
        out[key] = {
            "N_tokens": N, "V_types": V, "n1_volume": n1_vol,
            "min_match_seen": None if min_match == float("inf") else int(min_match),
            "P_vol": (n1_vol / N) if N else None,      # identically 0: censored
            "P_vn": (V / N) if N else None,            # realized productivity
        }
    return out
