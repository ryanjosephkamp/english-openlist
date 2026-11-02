"""
Stage 4 Sampling Frame

The synthetic intake after the comparatives were demoted: 48,361 plurals, past
tenses, gerunds and prefixed forms, all still marked `validated: true` with no
evidence behind it.

Same method as stage 3, which worked: look up the *stem* and read the
inflections Merriam-Webster records for it in `meta.stems`. Asking whether
`abacaviring` is a headword would return "not found" and prove nothing; asking
whether MW lists it among the forms of `abacavir` is a real question with a real
answer.

Stratified by **which inflection is being claimed**, because that is what
predicts whether it is plausible at all. A plural of a noun is ordinary English;
a plural of a gerund usually is not; and a past tense of a drug name is the
generator having no idea what part of speech it is affixing.

Usage:
    python scripts/build_stage4_frame.py --data-dir .cache/hf
"""

import argparse
import csv
import json
import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

FRAME_FIELDS = ["stem", "stratum", "in_wordnet", "wordnet_pos",
                "forms", "n_forms", "stem_intake"]

#: Longest suffix first, so `-ings` is not mistaken for `-s`.
#: Each entry is (suffix, stratum, [what to append after stripping]).
SUFFIX_RULES = [
    ("ings", "gerund-plural", ["", "e"]),
    ("ers",  "agent-plural",  ["", "e"]),
    ("ing",  "verb-form",     ["", "e"]),
    ("ed",   "verb-form",     ["", "e"]),
    ("es",   "plural",        ["", "e"]),
    ("s",    "plural",        [""]),
]

STRATA = ("plural", "gerund-plural", "verb-form", "agent-plural")


def candidate_stems(word: str, suffix: str, extras: list[str]) -> list[str]:
    """Plausible stems for one suffix, allowing for English spelling changes."""
    base = word[: -len(suffix)]
    out = [base + extra for extra in extras]
    if len(base) >= 4 and base[-1] == base[-2] and base[-1] not in "aeiou":
        out.append(base[:-1])                 # undo consonant doubling
    if base.endswith("i"):
        out.append(base[:-1] + "y")           # undo y -> i
    return out


def wordnet_pos(stem: str) -> set[str]:
    from nltk.corpus import wordnet as wn
    return {s.pos() for s in wn.synsets(stem)}


def build_frame(valid_dict: dict, exclude: set[str]) -> list[dict]:
    all_words = set(valid_dict)
    synthetic = [w for w, e in valid_dict.items()
                 if e.get("source") == "synthetic_generation" and w not in exclude]
    logger.info("Synthetic words to frame: %d", len(synthetic))

    # stem -> stratum -> forms. A stem can carry more than one kind of inflection
    # (`abacavirs` and `abacaviring` share `abacavir`), and they are different
    # claims, so they are kept apart.
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    unresolved = 0

    for word in synthetic:
        placed = False
        for suffix, stratum, extras in SUFFIX_RULES:
            if not word.endswith(suffix) or len(word) - len(suffix) < 3:
                continue
            stem = next((s for s in candidate_stems(word, suffix, extras)
                         if s in all_words), None)
            if stem is not None:
                grouped[(stem, stratum)].append(word)
                placed = True
                break
        if not placed:
            unresolved += 1

    logger.info("  placed: %d", sum(len(v) for v in grouped.values()))
    logger.info("  no stem in the list (skipped): %d", unresolved)

    rows = []
    for (stem, stratum) in sorted(grouped):
        pos = wordnet_pos(stem)
        rows.append({
            "stem": stem,
            "stratum": stratum,
            "in_wordnet": bool(pos),
            "wordnet_pos": "".join(sorted(pos)),
            "forms": " ".join(sorted(grouped[(stem, stratum)])),
            "n_forms": len(grouped[(stem, stratum)]),
            "stem_intake": valid_dict[stem].get("source") or "",
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the stage 4 sampling frame")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("corrections/stage4_frame.csv"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    with open(args.data_dir / "merged_valid_dict.json", "r", encoding="utf-8") as f:
        valid_dict = json.load(f)

    # blameworthier/blameworthiest survived stage 3 because Merriam-Webster
    # confirmed them. They are settled; do not re-ask.
    exclude = set()
    stage3 = Path("corrections/ledger_stage3.csv")
    if stage3.exists():
        with open(stage3, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                exclude.update(row["forms_listed"].split())
    if exclude:
        logger.info("Excluding %d form(s) already confirmed by MW: %s",
                    len(exclude), ", ".join(sorted(exclude)))

    rows = build_frame(valid_dict, exclude)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FRAME_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    stems: dict[str, int] = defaultdict(int)
    forms: dict[str, int] = defaultdict(int)
    known: dict[str, int] = defaultdict(int)
    for row in rows:
        stems[row["stratum"]] += 1
        forms[row["stratum"]] += row["n_forms"]
        known[row["stratum"]] += 1 if row["in_wordnet"] else 0

    logger.info("Wrote %d stem/inflection groups to %s", len(rows), args.out)
    for stratum in STRATA:
        logger.info("  %-14s %5d stems covering %6d forms  (%d stems in WordNet)",
                    stratum, stems[stratum], forms[stratum], known[stratum])
    logger.info("  %-14s %5d stems covering %6d forms",
                "total", len(rows), sum(forms.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
