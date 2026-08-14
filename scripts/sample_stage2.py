"""
Stage 2 Sampler

Draws the 400 words stage 2 will look up, stratified by corpus attestation.

The sample is committed before any API call is made. That ordering is the whole
point: a sample chosen after seeing results is not a sample, and there would be
no way for a reader to tell the difference afterwards.

Selection is deterministic and reproducible by hand. Rather than leaning on
`random.sample`, whose internals are free to change between Python releases,
each word is ranked by `sha256(seed:stratum:word)` and the lowest `n` are taken.
Anyone can recompute that in any language and get the same 400 words.

Usage:
    python scripts/sample_stage2.py --seed 20260814
"""

import argparse
import csv
import hashlib
import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

#: Sizes agreed for this stage. Deliberately not proportional: stratum 0 holds
#: only 448 words but is the most likely place for the LLM to have been right,
#: so it is oversampled to say something useful about it rather than nothing.
SAMPLE_SIZES = {
    "1": 160,
    "2": 80,
    "3": 60,
    "4+": 60,
    "0": 40,
}

SAMPLE_FIELDS = [
    "word",
    "stratum",
    "n_valid_sources",
    "all_unlikely",
    "pipeline_checks_passed",
    "gemini_source",
    "seed",
    "rank_key",
]


def rank_key(seed: int, stratum: str, word: str) -> str:
    """
    A word's position in its stratum's draw.

    Salted with the stratum so a word's rank in one stratum tells you nothing
    about any other, and with the seed so the draw can be repeated or redrawn
    deliberately rather than by accident.
    """
    return hashlib.sha256(f"{seed}:{stratum}:{word}".encode("utf-8")).hexdigest()


def draw(frame: list[dict], seed: int, sizes: dict[str, int]) -> list[dict]:
    """Take the lowest-ranked `sizes[stratum]` words from each stratum."""
    by_stratum: dict[str, list[dict]] = defaultdict(list)
    for row in frame:
        by_stratum[row["stratum"]].append(row)

    missing = set(sizes) - set(by_stratum)
    if missing:
        raise ValueError(f"frame has no words in stratum(s): {sorted(missing)}")

    sample: list[dict] = []
    for stratum in sorted(sizes):
        rows = by_stratum[stratum]
        wanted = sizes[stratum]
        if wanted > len(rows):
            raise ValueError(
                f"stratum {stratum!r} has {len(rows)} words, cannot draw {wanted}"
            )

        ranked = sorted(rows, key=lambda r: rank_key(seed, stratum, r["word"]))
        for row in ranked[:wanted]:
            sample.append({
                **row,
                "seed": seed,
                "rank_key": rank_key(seed, stratum, row["word"])[:16],
            })

    sample.sort(key=lambda r: (r["stratum"], r["word"]))
    return sample


def main() -> int:
    parser = argparse.ArgumentParser(description="Draw the stage 2 sample")
    parser.add_argument("--frame", type=Path, default=Path("corrections/stage2_frame.csv"))
    parser.add_argument("--out", type=Path, default=Path("corrections/stage2_sample.csv"))
    parser.add_argument("--seed", type=int, required=True,
                        help="Recorded in the output; changing it redraws the sample")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    with open(args.frame, "r", encoding="utf-8", newline="") as f:
        frame = list(csv.DictReader(f))
    logger.info("Frame: %d words", len(frame))

    sample = draw(frame, args.seed, SAMPLE_SIZES)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SAMPLE_FIELDS)
        writer.writeheader()
        writer.writerows(sample)

    counts: dict[str, int] = defaultdict(int)
    population: dict[str, int] = defaultdict(int)
    for row in frame:
        population[row["stratum"]] += 1
    for row in sample:
        counts[row["stratum"]] += 1

    logger.info("Sample written to %s (seed %d)", args.out, args.seed)
    for stratum in ("0", "1", "2", "3", "4+"):
        logger.info("  stratum %-3s : %3d of %5d  (%.1f%%)",
                    stratum, counts[stratum], population[stratum],
                    counts[stratum] / population[stratum] * 100)
    logger.info("  total       : %3d of %5d", len(sample), len(frame))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
