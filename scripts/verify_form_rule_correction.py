"""
Verify the form-rule correction independently of the script that applied it.

This does not trust the applier's own reconciliation. It compares the backup
against the live files and asserts that every single difference, in both
directions, is named by the ledger — and that the ledger contains nothing that
did not happen.

The point is that an unexplained delta of even one word fails the run.

Usage:
    python scripts/verify_form_rule_correction.py \
        --before ~/Documents/english-openlist-prune-mirror/form-rule-backup-2026-08-16 \
        --after .cache/hf --ledger corrections/ledger_form_rules.csv
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

FORM_RULE = re.compile(r"^[a-z]+$")

ok = True


def check(condition, label, detail=""):
    global ok
    print(f"  {'PASS' if condition else 'FAIL'}  {label}{('  ' + detail) if detail else ''}")
    if not condition:
        ok = False


def load(path):
    with open(path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", type=Path, required=True)
    ap.add_argument("--after", type=Path, required=True)
    ap.add_argument("--ledger", type=Path, required=True)
    args = ap.parse_args()

    bv = load(args.before / "merged_valid_words.txt")
    bi = load(args.before / "merged_invalid_words.txt")
    av = load(args.after / "merged_valid_words.txt")
    ai = load(args.after / "merged_invalid_words.txt")

    rows = list(csv.DictReader(open(args.ledger, encoding="utf-8", newline="")))
    led_del = {r["word"] for r in rows if r["action"] == "delete_malformed"}
    led_add = {r["word"] for r in rows if r["action"] == "add_candidate"}

    print("\n=== 1. no word was lost or gained without the ledger saying so ===")
    lost = (bv | bi) - (av | ai)
    gained = (av | ai) - (bv | bi)
    check(lost == led_del, "every string that left is a ledger deletion",
          f"left={len(lost)} ledger_deletes={len(led_del)}")
    check(gained == led_add, "every string that arrived is a ledger addition",
          f"arrived={len(gained)} ledger_adds={len(led_add)}")
    check(not (lost - led_del), "no unexplained departures",
          f"unexplained={sorted(lost - led_del)[:5]}")
    check(not (gained - led_add), "no unexplained arrivals",
          f"unexplained={sorted(gained - led_add)[:5]}")
    check(not (led_del - lost), "every ledger deletion actually happened")
    check(not (led_add - gained), "every ledger addition actually happened")

    print("\n=== 2. nothing crossed between lists unintentionally ===")
    promoted = (av - bv) - led_add          # invalid -> valid, not from the ledger
    demoted = (ai - bi) - led_add           # valid -> invalid, not from the ledger
    check(not promoted, "no word moved invalid -> valid",
          f"{sorted(promoted)[:5]}")
    check(not demoted, "no word moved valid -> invalid",
          f"{sorted(demoted)[:5]}")
    check((bv - av) == led_del & bv, "valid list lost exactly its ledger deletions")
    check((bi - ai) == led_del & bi, "invalid list lost exactly its ledger deletions")

    print("\n=== 3. the form rule now holds everywhere ===")
    bad_v = [w for w in av if not FORM_RULE.match(w)]
    bad_i = [w for w in ai if not FORM_RULE.match(w)]
    check(not bad_v, "valid list: zero form violations", f"{bad_v[:5]}")
    check(not bad_i, "invalid list: zero form violations", f"{bad_i[:5]}")
    check(not (av & ai), "no string on both lists")
    check(len(av | ai) == len(av) + len(ai), "no duplicates across the lists")

    print("\n=== 4. the universe arithmetic ===")
    before_n, after_n = len(bv | bi), len(av | ai)
    check(before_n == 9654152, "universe before = 9,654,152", f"got {before_n:,}")
    check(after_n == 9653999, "universe after  = 9,653,999", f"got {after_n:,}")
    check(before_n - len(led_del) + len(led_add) == after_n,
          f"{before_n:,} - {len(led_del)} + {len(led_add)} = {after_n:,}")
    check(len(av) == 345107, "valid list = 345,107", f"got {len(av):,}")

    print("\n=== 5. the 19 attested concatenations ===")
    NINETEEN = ["photorealistic", "hardshell", "highhanded", "hardnosed", "kneejerk",
                "getout", "longsuffering", "heavyhanded", "soso", "sawtoothed",
                "avantgarde", "bangup", "hardboiled", "highhat", "wellfounded",
                "wellread", "gogetting", "illhumored", "slowwitted"]
    present = [w for w in NINETEEN if w in av or w in ai]
    check(len(present) == 19, "all 19 present in the frame", f"{len(present)}/19")
    check(all(w in ai for w in NINETEEN), "all 19 are candidates, none auto-promoted")

    print("\n=== 6. the 26 single letters ===")
    letters = "abcdefghijklmnopqrstuvwxyz"
    missing = [L for L in letters if L not in av and L not in ai]
    check(not missing, "all 26 letters present in the frame", f"missing={missing}")

    print("\n=== 7. the dictionary tracks the valid list ===")
    d = json.load(open(args.after / "merged_valid_dict.json", encoding="utf-8"))
    check(set(d) <= av, "no dictionary key is absent from the valid list",
          f"orphans={sorted(set(d) - av)[:5]}")
    check(not (led_del & set(d)), "no deleted word kept a dictionary entry")

    print("\n" + "=" * 68)
    print("ALL VERIFICATION CHECKS PASSED" if ok else "VERIFICATION FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
