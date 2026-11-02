"""
Stage 3 Sampling Frame

Builds the population stage 3 samples from: the stems behind the synthetic
`-er`/`-est` forms.

64,837 words in the list came from a synthetic generator and carry no
attestation of any kind — no corpus source, no validation record — while every
one is marked `validated: true` and annotated "Synthetic candidate awaiting
validation". 16,478 of them are comparatives and superlatives: `abacteremicer`,
`abambulacralest`, `abatabler`. You cannot be "more abacteremic".

The unit of measurement is the **stem**, not the form. Merriam-Webster will never
carry `abacteremicer` as a headword, so asking about the form answers nothing.
Asking about `abacteremic` and then reading its `meta.stems` array — which is
where MW lists a headword's legitimate inflections — answers the real question:
does the dictionary recognise this comparative as a form of that word?

That also buys leverage. 16,478 forms reduce to 8,809 stems, so one lookup
speaks for 1.87 forms on average.

WordNet membership is computed here, at frame-build time, and written into the
frame. CI then never needs nltk or its 30 MB corpus to draw or check the sample.

Usage:
    python scripts/build_stage3_frame.py --data-dir .cache/hf
"""

import argparse
import csv
import json
import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

FRAME_FIELDS = [
    "stem",
    "stratum",
    "in_wordnet",
    "wordnet_pos",
    "forms",
    "n_forms",
    "stem_intake",
]

#: Undoing one suffix, with the orthographic variants English actually uses.
#: Deliberately generous: a stem that turns out not to be in the list is simply
#: not resolved, and over-generating candidates costs nothing but a set lookup.
SUFFIX_RULES = [
    ("est", ["", "e"]),
    ("er", ["", "e"]),
]


def candidate_stems(word: str) -> list[str]:
    """Every plausible stem of a comparative or superlative."""
    out = []
    for suffix, extras in SUFFIX_RULES:
        if not word.endswith(suffix) or len(word) - len(suffix) < 3:
            continue
        base = word[: -len(suffix)]
        for extra in extras:
            out.append(base + extra)
        # doubled final consonant: `redder` -> `red`
        if len(base) >= 4 and base[-1] == base[-2] and base[-1] not in "aeiou":
            out.append(base[:-1])
        # y -> i: `happier` -> `happy`
        if base.endswith("i"):
            out.append(base[:-1] + "y")
    return out


def wordnet_pos(stem: str) -> set[str]:
    """POS tags WordNet knows for the stem, empty when it has never heard of it."""
    from nltk.corpus import wordnet as wn
    return {s.pos() for s in wn.synsets(stem)}


def classify(pos: set[str]) -> str:
    """
    Three strata, chosen because they predict whether a source can rule at all.

    `wn-adj`      WordNet has it as an adjective. A comparative is at least
                  grammatically conceivable, so the question is real.
    `wn-other`    WordNet has it, but only as a noun or verb. A comparative on
                  it is bogus on its face and needs no dictionary to say so.
    `not-in-wn`   WordNet has never heard of it. The largest group, and the one
                  where nothing can be assumed.
    """
    if not pos:
        return "not-in-wn"
    if pos & {"a", "s"}:
        return "wn-adj"
    return "wn-other"


def build_frame(valid_dict: dict) -> list[dict]:
    all_words = set(valid_dict)
    synthetic = [w for w, e in valid_dict.items()
                 if e.get("source") == "synthetic_generation"]

    by_stem: dict[str, list[str]] = defaultdict(list)
    unresolved = 0

    for word in synthetic:
        if not word.endswith(("er", "est")):
            continue
        stem = next((s for s in candidate_stems(word) if s in all_words), None)
        if stem is None:
            unresolved += 1
            continue
        by_stem[stem].append(word)

    logger.info("-er/-est synthetic forms with a stem in the list: %d",
                sum(len(v) for v in by_stem.values()))
    logger.info("  distinct stems: %d", len(by_stem))
    logger.info("  forms whose stem is not in the list: %d", unresolved)

    rows = []
    for stem in sorted(by_stem):
        pos = wordnet_pos(stem)
        rows.append({
            "stem": stem,
            "stratum": classify(pos),
            "in_wordnet": bool(pos),
            "wordnet_pos": "".join(sorted(pos)),
            "forms": " ".join(sorted(by_stem[stem])),
            "n_forms": len(by_stem[stem]),
            "stem_intake": valid_dict[stem].get("source") or "",
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the stage 3 sampling frame")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("corrections/stage3_frame.csv"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    with open(args.data_dir / "merged_valid_dict.json", "r", encoding="utf-8") as f:
        valid_dict = json.load(f)
    logger.info("Loaded %d dictionary entries", len(valid_dict))

    rows = build_frame(valid_dict)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FRAME_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    counts: dict[str, int] = defaultdict(int)
    forms: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["stratum"]] += 1
        forms[row["stratum"]] += row["n_forms"]

    logger.info("Wrote %d stems to %s", len(rows), args.out)
    for stratum in ("wn-adj", "wn-other", "not-in-wn"):
        logger.info("  %-10s %5d stems covering %6d forms",
                    stratum, counts[stratum], forms[stratum])
    logger.info("  %-10s %5d stems covering %6d forms",
                "total", len(rows), sum(forms.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
