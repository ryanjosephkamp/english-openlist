"""
Apply the form-rule correction ledger.

The ledger decides; this script only carries the decision out, and refuses to do
anything the ledger does not say. Same posture as
`apply_correction_ledger.py` and `demote_words.py`, with one important
difference: **this is the only script in the project that deletes a string
outright.**

That deserves a guard rather than a comment, so every `delete_malformed` row is
re-checked here against the form rule before anything happens. If a word named
for deletion actually satisfies `^[a-z]+$`, the ledger is wrong and the run
aborts. The script cannot be used to delete a legitimate word even if the ledger
asks it to.

Symmetrically, `add_candidate` refuses to add a string that fails the form rule,
and refuses to add one already present — the frame must not gain duplicates.

Candidates are added to the **invalid list**, which is this project's pool of
strings awaiting evidence. Nothing here promotes anything to the valid list.
Attestation is evidence, not a verdict (D-001), so even the words backed by three
Scrabble dictionaries arrive as candidates.

Usage:
    python scripts/apply_form_rule_ledger.py --data-dir .cache/hf \
        --ledger corrections/ledger_form_rules.csv --dry-run
    python scripts/apply_form_rule_ledger.py --data-dir .cache/hf \
        --ledger corrections/ledger_form_rules.csv
"""

import argparse
import csv
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

KNOWN_ACTIONS = {"delete_malformed", "add_candidate", "none"}
FORM_RULE = re.compile(r"^[a-z]+$")
RECHECK_QUEUE_FILE = Path("corrections/recheck_queue.txt")


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


def write_recheck_queue(words: list[str], path: Path, note: str) -> int:
    """
    Add words to the queue the nightly draws from, matching the format
    `demote_words.py` writes.

    Every `add_candidate` row carries `recheck_queued: yes`, and that has to be
    true rather than aspirational. It matters most for the shortest additions:
    the nightly's `is_likely_english` pre-filter drops anything under 3
    characters, and its vowel-ratio band cannot be satisfied by a 1-character
    string at all, so a single letter would otherwise sit in the candidate pool
    permanently unexamined. The recheck queue is the one path that bypasses that
    filter.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if path.exists():
        existing = [l.strip() for l in open(path, encoding="utf-8")
                    if l.strip() and not l.startswith("#")]

    combined = sorted(set(existing) | set(words))
    with open(path, "w", encoding="utf-8") as f:
        f.write("# Words this project moved off the valid list, or added as new\n")
        f.write("# candidates that the nightly pre-filter would otherwise skip.\n")
        f.write("#\n")
        f.write("# The nightly run reserves part of each night for this queue and\n")
        f.write("# ignores the pre-filter that would otherwise hide the shortest\n")
        f.write("# and longest entries, so every one of them gets looked at.\n")
        f.write("# See corrections/README.md.\n")
        f.write(f"#\n# {note}\n")
        f.write(f"# {len(combined)} words\n")
        for word in combined:
            f.write(f"{word}\n")
    return len(combined)


def check_ledger(rows: list[dict], valid: set[str], invalid: set[str]) -> None:
    """
    Refuse the whole run if any row is unsafe. Checked before anything is
    written, so a bad ledger costs nothing.
    """
    problems = []
    for r in rows:
        word, action = r["word"], r["action"]
        if action not in KNOWN_ACTIONS:
            problems.append(f"{word!r}: unrecognised action {action!r}")
            continue

        if action == "delete_malformed":
            if FORM_RULE.match(word):
                problems.append(
                    f"{word!r}: ledger says delete as malformed, but it SATISFIES "
                    f"^[a-z]+$. This script will not delete a legitimate word.")
            if word not in valid and word not in invalid:
                problems.append(f"{word!r}: marked for deletion but not present")

        elif action == "add_candidate":
            if not FORM_RULE.match(word):
                problems.append(
                    f"{word!r}: ledger says add, but it fails ^[a-z]+$")
            if word in valid or word in invalid:
                problems.append(f"{word!r}: marked for addition but already present")

    if problems:
        for p in problems:
            logger.error(p)
        raise ValueError(f"{len(problems)} ledger rows are unsafe; nothing written")


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply the form-rule correction ledger")
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--dry-run", action="store_true",
                    help="Report what would change, write nothing")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    valid_path = args.data_dir / "merged_valid_words.txt"
    invalid_path = args.data_dir / "merged_invalid_words.txt"
    dict_path = args.data_dir / "merged_valid_dict.json"

    valid = set(load_word_list(valid_path))
    invalid = set(load_word_list(invalid_path))
    v0, i0 = len(valid), len(invalid)
    logger.info("Before: valid=%d invalid=%d universe=%d", v0, i0, v0 + i0)

    rows = read_ledger(args.ledger)
    logger.info("Ledger rows: %d", len(rows))
    check_ledger(rows, valid, invalid)
    logger.info("Ledger passes every safety precondition")

    deleted_valid, deleted_invalid, added = [], [], []
    for r in rows:
        word, action = r["word"], r["action"]
        if action == "delete_malformed":
            if word in valid:
                valid.discard(word)
                deleted_valid.append(word)
            if word in invalid:
                invalid.discard(word)
                deleted_invalid.append(word)
        elif action == "add_candidate":
            invalid.add(word)
            added.append(word)

    # The dictionary is keyed by valid words; deleted ones lose their entries.
    with open(dict_path, "r", encoding="utf-8") as f:
        valid_dict = json.load(f)
    dict_removed = [w for w in deleted_valid if w in valid_dict]
    for w in dict_removed:
        del valid_dict[w]

    logger.info("Deleted from valid list   : %d", len(deleted_valid))
    logger.info("Deleted from invalid list : %d", len(deleted_invalid))
    logger.info("Added as candidates       : %d", len(added))
    logger.info("Dictionary entries removed: %d", len(dict_removed))
    logger.info("After: valid=%d invalid=%d universe=%d",
                len(valid), len(invalid), len(valid) + len(invalid))

    # Reconciliation. Every count must be explained by the ledger.
    n_del = sum(1 for r in rows if r["action"] == "delete_malformed")
    n_add = sum(1 for r in rows if r["action"] == "add_candidate")
    assert len(deleted_valid) + len(deleted_invalid) == n_del, "deletions do not reconcile"
    assert len(added) == n_add, "additions do not reconcile"
    assert (v0 + i0) - n_del + n_add == len(valid) + len(invalid), \
        "universe does not reconcile"
    assert not (valid & invalid), "a word ended up on both lists"
    assert all(FORM_RULE.match(w) for w in valid), "valid list still has malformed entries"
    assert all(FORM_RULE.match(w) for w in invalid), "invalid list still has malformed entries"
    assert set(valid_dict) <= valid, "dictionary holds keys that are not valid words"
    logger.info("Reconciliation OK — both lists are now form-clean")

    if args.dry_run:
        logger.info("Dry run: nothing written")
        return 0

    write_word_list(valid, valid_path)
    write_word_list(invalid, invalid_path)
    with open(dict_path, "w", encoding="utf-8") as f:
        json.dump(valid_dict, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %s, %s and %s", valid_path, invalid_path, dict_path)

    if added:
        total = write_recheck_queue(
            added, RECHECK_QUEUE_FILE,
            f"{len(added)} added by the form-rule correction, {args.ledger.name}")
        logger.info("Recheck queue now holds %d words (%s)", total, RECHECK_QUEUE_FILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
