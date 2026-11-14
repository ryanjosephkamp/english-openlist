"""
Correction Ledger Builder

Builds the ledger that the data correction works from. The ledger is the source
of truth: every verdict is recorded here with the evidence that decided it, and
the word lists are regenerated from it. That way a decision can be revisited
without re-running anything, and nothing is ever moved without a recorded reason.

Stage 1 covers the words that appear in *both* the valid and the invalid list.
That is logically impossible and must be resolved one way or the other.

Each of those words already carries a dictionary API ruling inside
merged_valid_dict.json — Merriam-Webster, Merriam-Webster Medical or Free
Dictionary, most of them with the full raw response still attached. So the
verdict comes from a recorded authority, not from a fresh lookup and not from
anybody's judgement. Method is logged as `stored_api_ruling` so it can be told
apart from anything decided another way.

Usage:
    python scripts/build_correction_ledger.py --data-dir .cache/hf
    python scripts/build_correction_ledger.py --data-dir .cache/hf --out corrections/
"""

import argparse
import csv
import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

# Sources we accept as authoritative for a stage 1 verdict. Anything outside
# this set means the entry was not decided by a dictionary API and stage 1
# should not be ruling on it.
AUTHORITATIVE_SOURCES = {
    "merriam-webster",
    "merriam-webster-medical",
    "free-dictionary",
}

LEDGER_FIELDS = [
    "word",
    "stage",
    "verdict",
    "action",
    "method",
    "source",
    "confidence",
    "evidence",
    "part_of_speech",
    "decided_date",
]


def load_word_list(path: Path) -> set[str]:
    """Read one word per line, ignoring blanks."""
    with open(path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def find_dual_listed(valid_words: set[str], invalid_words: set[str]) -> list[str]:
    """Words present in both lists. Sorted, so the ledger is reproducible."""
    return sorted(valid_words & invalid_words)


def describe_evidence(entry: dict) -> str:
    """
    Summarise what is actually recorded on the entry, in a form a stranger can
    check. Says what is there rather than asserting a conclusion.
    """
    bits = []
    if entry.get("raw_response"):
        bits.append("raw_response")
    if entry.get("definition"):
        bits.append("definition")
    if entry.get("etymology"):
        bits.append("etymology")
    if entry.get("pronunciation"):
        bits.append("pronunciation")
    return "+".join(bits) if bits else "none"


def build_stage1_rows(dual_listed: list[str], valid_dict: dict,
                      decided: str) -> tuple[list[dict], list[str]]:
    """
    One ledger row per dual-listed word.

    Returns (rows, unresolved). A word lands in `unresolved` if its entry has no
    authoritative source — stage 1 declines to rule on those rather than
    guessing, and they are reported so they can be picked up deliberately.
    """
    rows, unresolved = [], []

    for word in dual_listed:
        entry = valid_dict.get(word)
        if entry is None:
            unresolved.append(word)
            logger.warning("%s is dual-listed but absent from the valid dict", word)
            continue

        source = entry.get("source")
        if source not in AUTHORITATIVE_SOURCES:
            unresolved.append(word)
            logger.warning("%s has no authoritative source (source=%r)", word, source)
            continue

        rows.append({
            "word": word,
            "stage": "1",
            "verdict": "valid",
            # The word stays valid. What changes is that it stops also being
            # listed as invalid, which it never should have been.
            "action": "remove_from_invalid_list",
            "method": "stored_api_ruling",
            "source": source,
            "confidence": "high",
            "evidence": describe_evidence(entry),
            "part_of_speech": entry.get("part_of_speech") or "",
            "decided_date": decided,
        })

    return rows, unresolved


def write_ledger(rows: list[dict], path: Path) -> None:
    """Write the ledger as CSV. CSV keeps it diffable and out of the *.json ignore rule."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to %s", len(rows), path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the correction ledger")
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="Directory holding the merged_* data files")
    parser.add_argument("--out", type=Path, default=Path("corrections"),
                        help="Directory to write the ledger into")
    parser.add_argument("--decided-date", default=date.today().isoformat(),
                        help="Date recorded on each verdict (default: today)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    valid_words = load_word_list(args.data_dir / "merged_valid_words.txt")
    invalid_words = load_word_list(args.data_dir / "merged_invalid_words.txt")
    logger.info("Loaded %d valid, %d invalid", len(valid_words), len(invalid_words))

    with open(args.data_dir / "merged_valid_dict.json", "r", encoding="utf-8") as f:
        valid_dict = json.load(f)

    dual_listed = find_dual_listed(valid_words, invalid_words)
    logger.info("Dual-listed words: %d", len(dual_listed))

    rows, unresolved = build_stage1_rows(dual_listed, valid_dict, args.decided_date)

    write_ledger(rows, args.out / "ledger_stage1.csv")

    if unresolved:
        # Not a failure — a stop. These need a decision made some other way, and
        # saying so is better than quietly ruling on them.
        logger.warning("%d dual-listed words could not be decided from stored "
                       "evidence and are left in place: %s",
                       len(unresolved), ", ".join(unresolved))
        (args.out / "stage1_unresolved.txt").write_text(
            "\n".join(unresolved) + "\n", encoding="utf-8")

    logger.info("Stage 1 ledger complete: %d resolved, %d unresolved",
                len(rows), len(unresolved))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
