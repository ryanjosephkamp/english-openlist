"""
Correction Ledger Applier

Regenerates the word lists from the ledger. The ledger decides; this script only
carries the decision out, and refuses to do anything the ledger does not say.

It is deliberately conservative:

  * every action must be one it recognises, or it stops
  * it will not remove a word from the invalid list unless that word is in the
    valid list, because that would be deleting a word rather than correcting one
  * it reports the before and after counts and checks they reconcile
  * --dry-run does everything except write

It also normalises `status` values that leaked a Python enum repr into the JSON
("WordStatus.VALID" instead of "valid"). That is a serialisation bug, not a
verdict, so it is repaired everywhere it appears rather than only on the words
this stage touches.

Usage:
    python scripts/apply_correction_ledger.py --data-dir .cache/hf --ledger corrections/ledger_stage1.csv --dry-run
    python scripts/apply_correction_ledger.py --data-dir .cache/hf --ledger corrections/ledger_stage1.csv
"""

import argparse
import csv
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

KNOWN_ACTIONS = {"remove_from_invalid_list"}

# The enum repr that leaked into `status`. str(WordStatus.VALID) rather than
# WordStatus.VALID.value — see scripts/dictionary_api.py.
ENUM_LEAK = "WordStatus.VALID"
ENUM_LEAK_FIX = "valid"


def load_word_list(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def write_word_list(words, path: Path) -> None:
    """Sorted, one per line, trailing newline — the format the pipeline writes."""
    with open(path, "w", encoding="utf-8") as f:
        for word in sorted(words):
            f.write(f"{word}\n")


def read_ledger(path: Path) -> list[dict]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def apply_removals(rows: list[dict], valid: set[str],
                   invalid: set[str]) -> tuple[set[str], list[str]]:
    """
    Apply `remove_from_invalid_list` rows. Returns (new_invalid, removed).

    Refuses to remove a word that is not in the valid list: the ledger's claim is
    that the word belongs on the valid side, and if it is not there, the premise
    is wrong and the row should be re-examined rather than executed.
    """
    removed, skipped = [], []
    new_invalid = set(invalid)

    for row in rows:
        action = row["action"]
        if action not in KNOWN_ACTIONS:
            raise ValueError(
                f"ledger row for {row['word']!r} has unrecognised action {action!r}"
            )

        word = row["word"]
        if word not in valid:
            skipped.append(word)
            logger.error("%s: ledger says remove from invalid, but it is not in "
                         "the valid list. Skipping.", word)
            continue
        if word not in new_invalid:
            # Already correct — the pipeline may have fixed it overnight.
            logger.info("%s: already absent from the invalid list, nothing to do", word)
            continue

        new_invalid.discard(word)
        removed.append(word)

    if skipped:
        raise ValueError(
            f"{len(skipped)} ledger rows could not be applied safely: "
            f"{', '.join(skipped)}"
        )

    return new_invalid, removed


def normalise_status(valid_dict: dict) -> int:
    """Repair the leaked enum repr in `status`. Returns how many were fixed."""
    fixed = 0
    for entry in valid_dict.values():
        if entry.get("status") == ENUM_LEAK:
            entry["status"] = ENUM_LEAK_FIX
            fixed += 1
    return fixed


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply the correction ledger")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change, write nothing")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    valid_path = args.data_dir / "merged_valid_words.txt"
    invalid_path = args.data_dir / "merged_invalid_words.txt"
    dict_path = args.data_dir / "merged_valid_dict.json"

    valid = set(load_word_list(valid_path))
    invalid = set(load_word_list(invalid_path))
    valid_before, invalid_before = len(valid), len(invalid)
    logger.info("Before: valid=%d invalid=%d", valid_before, invalid_before)

    rows = read_ledger(args.ledger)
    logger.info("Ledger rows: %d", len(rows))

    new_invalid, removed = apply_removals(rows, valid, invalid)

    with open(dict_path, "r", encoding="utf-8") as f:
        valid_dict = json.load(f)
    fixed = normalise_status(valid_dict)

    logger.info("Removed from invalid list : %d", len(removed))
    logger.info("status enum repr repaired : %d", fixed)
    logger.info("After: valid=%d invalid=%d", len(valid), len(new_invalid))

    # Reconciliation. The valid list is untouched by stage 1; the invalid list
    # loses exactly the words the ledger named.
    assert len(valid) == valid_before, "stage 1 must not change the valid list"
    assert invalid_before - len(new_invalid) == len(removed), "invalid count does not reconcile"
    assert not (valid & new_invalid), "words still appear in both lists"
    logger.info("Reconciliation OK — no word is in both lists")

    if args.dry_run:
        logger.info("Dry run: nothing written")
        return 0

    write_word_list(new_invalid, invalid_path)
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(valid_dict, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %s and %s", invalid_path, dict_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
