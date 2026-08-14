"""
Stage 3 Sampler

Draws the stems stage 3 will look up, stratified by whether WordNet knows them.

Same discipline as stage 2: committed before any lookup runs, and selected by
`sha256(seed:stratum:stem)` rather than `random.sample`, so anyone can recompute
the draw in any language and check it was not chosen after seeing results.

Usage:
    python scripts/sample_stage3.py --seed 20260814
"""

import argparse
import csv
import logging
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.sample_stage2 import rank_key

logger = logging.getLogger(__name__)

#: Not proportional. `wn-other` holds only 306 stems but is the group where a
#: comparative is bogus on its face, so it is oversampled to say something about
#: it rather than nothing. `not-in-wn` is the biggest group and the one where
#: coverage is most in doubt, so it takes the largest share.
SAMPLE_SIZES = {
    "wn-adj": 100,
    "wn-other": 50,
    "not-in-wn": 150,
}

SAMPLE_FIELDS = [
    "stem", "stratum", "in_wordnet", "wordnet_pos",
    "forms", "n_forms", "stem_intake", "seed", "rank_key",
]


def draw(frame: list[dict], seed: int, sizes: dict[str, int]) -> list[dict]:
    by_stratum: dict[str, list[dict]] = defaultdict(list)
    for row in frame:
        by_stratum[row["stratum"]].append(row)

    missing = set(sizes) - set(by_stratum)
    if missing:
        raise ValueError(f"frame has no stems in stratum(s): {sorted(missing)}")

    sample: list[dict] = []
    for stratum in sorted(sizes):
        rows = by_stratum[stratum]
        wanted = sizes[stratum]
        if wanted > len(rows):
            raise ValueError(
                f"stratum {stratum!r} has {len(rows)} stems, cannot draw {wanted}")

        ranked = sorted(rows, key=lambda r: rank_key(seed, stratum, r["stem"]))
        for row in ranked[:wanted]:
            sample.append({
                **row,
                "seed": seed,
                "rank_key": rank_key(seed, stratum, row["stem"])[:16],
            })

    sample.sort(key=lambda r: (r["stratum"], r["stem"]))
    return sample


def main() -> int:
    parser = argparse.ArgumentParser(description="Draw the stage 3 sample")
    parser.add_argument("--frame", type=Path, default=Path("corrections/stage3_frame.csv"))
    parser.add_argument("--out", type=Path, default=Path("corrections/stage3_sample.csv"))
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--sizes", default=None,
                        help="stratum=n,stratum=n — defaults to the stage 3 sizes. "
                             "The frame's own strata decide what is valid here.")
    args = parser.parse_args()

    sizes = SAMPLE_SIZES
    if args.sizes:
        sizes = {}
        for part in args.sizes.split(","):
            name, _, count = part.partition("=")
            sizes[name.strip()] = int(count)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    with open(args.frame, "r", encoding="utf-8", newline="") as f:
        frame = list(csv.DictReader(f))
    logger.info("Frame: %d stems", len(frame))

    sample = draw(frame, args.seed, sizes)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SAMPLE_FIELDS)
        writer.writeheader()
        writer.writerows(sample)

    population: dict[str, int] = defaultdict(int)
    drawn: dict[str, int] = defaultdict(int)
    forms: dict[str, int] = defaultdict(int)
    for row in frame:
        population[row["stratum"]] += 1
    for row in sample:
        drawn[row["stratum"]] += 1
        forms[row["stratum"]] += int(row["n_forms"])

    logger.info("Sample written to %s (seed %d)", args.out, args.seed)
    for stratum in sorted(sizes):
        logger.info("  %-14s %3d of %5d stems  (%.1f%%), covering %4d forms",
                    stratum, drawn[stratum], population[stratum],
                    drawn[stratum] / population[stratum] * 100, forms[stratum])
    logger.info("  %-10s %3d of %5d stems, covering %4d forms",
                "total", len(sample), len(frame), sum(forms.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
