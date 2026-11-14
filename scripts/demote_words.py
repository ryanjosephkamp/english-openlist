"""
Demote words from the valid list to the invalid list.

This is the only script in the project that takes a word off the valid list, and
it is deliberately hard to use casually. It works from a ledger: a file naming
every word, why it is being moved, what evidence decided it, and when. It will
not move a word the ledger does not name, and it records enough that the
decision can be argued with later.

**A demotion here is not a verdict that a word is not English.** It says no
dictionary we could reach recognised it on the date in the ledger. Dictionaries
gain entries; some of these forms may yet be attested. So every demoted word is
written to the recheck queue, which the nightly run examines on a reserved slice
of its budget, bypassing the pre-filter that would otherwise hide the longer
ones for good. `reversible` is `yes` on every row, and it means it.

Usage:
    python scripts/demote_words.py --data-dir .cache/hf --ledger corrections/ledger_demotions.csv --dry-run
    python scripts/demote_words.py --data-dir .cache/hf --ledger corrections/ledger_demotions.csv
"""

import argparse
import csv
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

KNOWN_ACTIONS = {"demote_to_invalid"}

LEDGER_FIELDS = [
    "word", "stage", "action", "reason", "method", "source", "evidence",
    "confidence", "reversible", "recheck_queued", "category", "decided_date",
]


def load_word_list(path: Path) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def write_word_list(words, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for word in sorted(words):
            f.write(f"{word}\n")


def apply_demotions(rows: list[dict], valid: set[str], invalid: set[str]
                    ) -> tuple[set[str], set[str], list[str]]:
    """
    Move the ledger's words from valid to invalid.

    Refuses on anything it does not recognise, and refuses to "demote" a word
    that is not on the valid list — that would silently add a word to the invalid
    list under cover of a correction.
    """
    moved, missing = [], []
    new_valid, new_invalid = set(valid), set(invalid)

    for row in rows:
        if row["action"] not in KNOWN_ACTIONS:
            raise ValueError(
                f"ledger row for {row['word']!r} has unrecognised action "
                f"{row['action']!r}")

        word = row["word"]
        if word not in new_valid:
            missing.append(word)
            continue

        new_valid.discard(word)
        new_invalid.add(word)
        moved.append(word)

    if missing:
        raise ValueError(
            f"{len(missing)} ledger words are not on the valid list, so there is "
            f"nothing to demote: {', '.join(missing[:10])}"
            + (" …" if len(missing) > 10 else ""))

    return new_valid, new_invalid, moved


def write_recheck_queue(words: list[str], path: Path, note: str) -> None:
    """
    The queue the nightly run draws from. Sorted, so it is diffable, and headed
    by a note explaining to anyone who opens it why these words are here.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        existing = [l.strip() for l in open(path, encoding="utf-8")
                    if l.strip() and not l.startswith("#")]

    combined = sorted(set(existing) | set(words))
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Words this project moved off the valid list.\n")
        f.write("#\n")
        f.write("# They are here because no dictionary we could reach recognised\n")
        f.write("# them on the day they were demoted -- which is not the same as\n")
        f.write("# their not being words. The nightly run reserves part of each\n")
        f.write("# night for this queue and ignores the pre-filter that would\n")
        f.write("# otherwise hide the longer ones, so every one of them gets\n")
        f.write("# looked at again. See corrections/README.md.\n")
        f.write(f"#\n# {note}\n")
        f.write(f"# {len(combined)} words\n")
        for word in combined:
            f.write(f"{word}\n")
    logger.info("Recheck queue now holds %d words (%s)", len(combined), path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Demote words named by a ledger")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--queue", type=Path,
                        default=Path("corrections/recheck_queue.txt"))
    parser.add_argument("--note", default="")
    parser.add_argument("--dry-run", action="store_true")
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

    with open(args.ledger, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    logger.info("Ledger rows: %d", len(rows))

    if any(r.get("reversible") != "yes" for r in rows):
        raise ValueError("every demotion must be marked reversible")

    new_valid, new_invalid, moved = apply_demotions(rows, valid, invalid)

    with open(dict_path, "r", encoding="utf-8") as f:
        valid_dict = json.load(f)
    dropped = [w for w in moved if valid_dict.pop(w, None) is not None]

    logger.info("Demoted            : %d", len(moved))
    logger.info("Dict entries removed: %d", len(dropped))
    logger.info("After: valid=%d invalid=%d", len(new_valid), len(new_invalid))

    assert valid_before - len(new_valid) == len(moved), "valid count does not reconcile"
    assert len(new_invalid) - invalid_before == len(moved), "invalid count does not reconcile"
    assert not (new_valid & new_invalid), "a word ended up on both lists"
    assert len(valid_dict) == len(new_valid), "dict and valid list disagree"
    logger.info("Reconciliation OK — no word is on both lists")

    if args.dry_run:
        logger.info("Dry run: nothing written")
        return 0

    write_word_list(new_valid, valid_path)
    write_word_list(new_invalid, invalid_path)
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(valid_dict, f, indent=2, ensure_ascii=False)
    write_recheck_queue(moved, args.queue, args.note)
    logger.info("Wrote %s, %s and %s", valid_path, invalid_path, dict_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
