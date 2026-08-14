"""
Stage 2 Sampling Frame

Builds the population that stage 2 samples from: every word in the valid list
whose own record says `"status": "invalid"`.

Those 20,052 verdicts all came from one pass by a single LLM (Google Gemini 3
Flash Preview, December 2025) which also marked 117,653 other words valid. The
question stage 2 asks is how often that pass was wrong. Since nothing can be
concluded from a small unstratified sample about *which kinds* of word it got
wrong, the frame records each word's corpus attestation strength, and the sample
is drawn within those strata.

The frame is written as CSV and committed. It is only ~300 KB, it makes the
population auditable by someone who does not have the 291 MB dictionary, and it
means CI never has to download that dictionary to draw or check the sample.

Usage:
    python scripts/build_stage2_frame.py --data-dir .cache/hf
"""

import argparse
import csv
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

FRAME_FIELDS = [
    "word",
    "stratum",
    "n_valid_sources",
    "all_unlikely",
    "pipeline_checks_passed",
    "gemini_source",
]

#: Strata are "how many corpora said this looks like a real word". A word with
#: four independent corpora behind it is a very different case from one with
#: none, and lumping them together would hide exactly the pattern worth finding.
#: 4+ are pooled because the tail past four is thin.
STRATUM_LABELS = {0: "0", 1: "1", 2: "2", 3: "3", 4: "4+"}


def classify(entry: dict) -> dict:
    """Everything the frame records about one word, from its dictionary entry."""
    sources = entry.get("candidate_source") or []
    n_valid = sum(1 for s in sources if s.endswith("_valid"))

    # Every sub-validation that is present, and whether all of them passed. The
    # pipeline's own deterministic checks agreeing with each other while the LLM
    # disagrees is the shape that makes this set interesting.
    checks = []
    for key, field in (
        ("advanced_validation", "passed"),
        ("statistical_validation", "passed"),
        ("repeat_validation", "likely_valid"),
    ):
        value = entry.get(key)
        if isinstance(value, dict):
            checks.append(bool(value.get(field)))

    manual = entry.get("manual_validation") or {}

    return {
        "stratum": STRATUM_LABELS[min(n_valid, 4)],
        "n_valid_sources": n_valid,
        # Distinguishes the 307 words whose sources all said "unlikely" from the
        # 141 that carry no sources at all. Both land in stratum 0, but they are
        # not the same claim, and recording it here means the split can be
        # analysed later without drawing a new sample.
        "all_unlikely": bool(sources) and all(s.endswith("_unlikely") for s in sources),
        "pipeline_checks_passed": bool(checks) and all(checks),
        "gemini_source": manual.get("manual_validation_source", ""),
    }


def build_frame(valid_dict: dict) -> list[dict]:
    """One row per word carrying status:'invalid'. Sorted, so the frame is stable."""
    rows = []
    for word in sorted(valid_dict):
        entry = valid_dict[word]
        if entry.get("status") != "invalid":
            continue
        rows.append({"word": word, **classify(entry)})
    return rows


def write_frame(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FRAME_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to %s", len(rows), path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the stage 2 sampling frame")
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="Directory holding merged_valid_dict.json")
    parser.add_argument("--out", type=Path, default=Path("corrections/stage2_frame.csv"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    with open(args.data_dir / "merged_valid_dict.json", "r", encoding="utf-8") as f:
        valid_dict = json.load(f)
    logger.info("Loaded %d dictionary entries", len(valid_dict))

    rows = build_frame(valid_dict)
    write_frame(rows, args.out)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["stratum"]] = counts.get(row["stratum"], 0) + 1
    logger.info("Population by stratum:")
    for label in ("0", "1", "2", "3", "4+"):
        logger.info("  %-3s corpus sources : %6d", label, counts.get(label, 0))
    logger.info("  total               : %6d", len(rows))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
