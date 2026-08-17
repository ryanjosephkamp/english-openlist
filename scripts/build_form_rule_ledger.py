"""
Build the form-rule correction ledger.

The 2026-08-16 audit found 190 entries on the valid list that violate the
project's own form rule — 188 hyphenated and 2 accented. They have been there
since before the rule was written down; the site has quietly shipped a "Strictly
a–z" slice excluding exactly these 190 for some time.

This script writes the ledger. It decides nothing on its own: every row is
derived from a check it can re-run, and it re-runs all of them each time so the
ledger is reproducible rather than transcribed.

Three kinds of row:

  delete_malformed  the string fails ^[a-z]+$. It is not a candidate and never
                    was. This is the only action in the project that removes a
                    string outright, which is why it carries a hard precondition
                    the applier re-checks: the string must actually fail the
                    form rule.

  add_candidate     a form-valid string absent from both lists. Added to the
                    invalid list, which is the candidate pool — NOT to the valid
                    list. Attestation is evidence, never a verdict (D-001), so
                    even the 19 words backed by Scrabble dictionaries enter as
                    candidates and the model rules on them later.

  none              recorded for the audit trail, changes nothing.

Usage:
    python scripts/build_form_rule_ledger.py --data-dir .cache/hf \
        --wordlists <dir> --out corrections/ledger_form_rules.csv
"""

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

FORM_RULE = re.compile(r"^[a-z]+$")
DATE = "2026-08-16"

LEDGER_FIELDS = [
    "word", "stage", "action", "reason", "method", "source", "evidence",
    "confidence", "reversible", "recheck_queued", "category", "decided_date",
]


def load(path):
    with open(path, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def load_reference_sources(wordlists: Path):
    """The seven curated sources used to check concatenations."""
    from nltk.corpus import wordnet as wn

    def wl(fn, first_token=False):
        out = set()
        with open(wordlists / fn, encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.split()
                tok = (parts[0] if first_token and parts else line.strip()).lower()
                if tok.isalpha():
                    out.add(tok)
        return out

    return {
        "wordnet": {l.name().lower() for s in wn.all_synsets() for l in s.lemmas()},
        "web2": {w.strip().lower() for w in open("/usr/share/dict/words", errors="ignore")},
        "enable": wl("enable1.txt"),
        "sowpods": wl("sowpods.txt"),
        "nwl2023": wl("nwl2023.txt", True),
        "csw21": wl("csw21.txt", True),
        "words_alpha": wl("words_alpha.txt"),
    }


def row(word, action, reason, evidence, category, confidence="high",
        method="form_rule_audit_2026_08_16", source="scripts/word_validator.py"):
    return {
        "word": word, "stage": "form-rules", "action": action, "reason": reason,
        "method": method, "source": source, "evidence": evidence,
        "confidence": confidence, "reversible": "yes",
        "recheck_queued": "yes" if action == "add_candidate" else "no",
        "category": category, "decided_date": DATE,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, required=True)
    ap.add_argument("--wordlists", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    valid = load(args.data_dir / "merged_valid_words.txt")
    invalid = load(args.data_dir / "merged_invalid_words.txt")
    universe = valid | invalid
    src = load_reference_sources(args.wordlists)

    rows = []

    # ---- 1. malformed entries, deleted -------------------------------------
    malformed = sorted(w for w in universe if not FORM_RULE.match(w))
    fragments = [w for w in malformed if w.startswith("-") or w.endswith("-")]
    accented = [w for w in malformed if not w.isascii()]
    whole_hyphen = [w for w in malformed if w not in fragments and w not in accented]

    for w in fragments:
        stem = w.strip("-")
        where = ("already on the valid list" if stem in valid
                 else "already a candidate on the invalid list" if stem in invalid
                 else "NOT PRESENT")
        n = sum(1 for s in src.values() if stem in s)
        rows.append(row(
            w, "delete_malformed",
            f"truncated fragment of a hyphenated compound; stem '{stem}' is {where}",
            f"fails ^[a-z]+$; stem '{stem}' attested by {n}/7 curated sources",
            "hyphenated-fragment"))

    for w in whole_hyphen:
        cat = w.replace("-", "")
        hits = [n for n, s in src.items() if cat in s]
        where = ("valid list" if cat in valid else
                 "invalid list" if cat in invalid else "absent from the frame")
        rows.append(row(
            w, "delete_malformed",
            f"hyphenated compound; multi-token by the form rule",
            f"fails ^[a-z]+$; concatenation '{cat}' is on the {where}"
            + (f", attested by {','.join(hits)}" if hits else ", unattested"),
            "hyphenated-compound"))

    for w in accented:
        stripped = (w.replace("ñ", "n").replace("é", "e").replace("á", "a")
                     .replace("í", "i").replace("ó", "o").replace("ú", "u"))
        where = ("already on the valid list — this entry is a duplicate" if stripped in valid
                 else "already a candidate" if stripped in invalid
                 else "absent; added by this ledger")
        rows.append(row(
            w, "delete_malformed",
            "non-ASCII characters; the form rule is ASCII a-z only",
            f"fails ^[a-z]+$; unaccented form '{stripped}' is {where}",
            "accented"))

    # ---- 2. candidates added ------------------------------------------------
    added = set()

    # 2a. concatenations of the hyphenated entries that are absent from the frame
    for w in sorted(whole_hyphen):
        cat = w.replace("-", "")
        if cat in universe or cat in added or not FORM_RULE.match(cat):
            continue
        hits = [n for n, s in src.items() if cat in s]
        added.add(cat)
        rows.append(row(
            cat, "add_candidate",
            f"solid form of '{w}', which this ledger deletes; absent from the frame",
            (f"attested by {','.join(hits)}" if hits
             else "no curated source attests it; enters as an ordinary candidate"),
            "concatenation",
            confidence="high" if hits else "low"))

    # 2b. unaccented forms of the accented entries
    for w in sorted(accented):
        stripped = (w.replace("ñ", "n").replace("é", "e").replace("á", "a")
                     .replace("í", "i").replace("ó", "o").replace("ú", "u"))
        if stripped in universe or stripped in added or not FORM_RULE.match(stripped):
            continue
        added.add(stripped)
        rows.append(row(
            stripped, "add_candidate",
            f"unaccented form of '{w}', which this ledger deletes",
            "form-valid and absent from the frame", "accented-stripped",
            confidence="medium"))

    # 2c. the single letters absent from the frame (D-027)
    for letter in "abcdefghijklmnopqrstuvwxyz":
        if letter in universe or letter in added:
            continue
        added.add(letter)
        rows.append(row(
            letter, "add_candidate",
            "single letter, form-legal since D-025; a candidate, not an assertion",
            "no source can settle single letters: Scrabble lists hold none by rule, "
            "and Wiktionary gives 25 of 26 a word-level POS. Adjudicated on evidence.",
            "single-letter", confidence="low",
            method="rule_change_D-025", source="research/DECISIONS.md D-027"))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        w.writeheader()
        w.writerows(rows)

    dele = sum(1 for r in rows if r["action"] == "delete_malformed")
    add = sum(1 for r in rows if r["action"] == "add_candidate")
    print(f"ledger written: {args.out}")
    print(f"  delete_malformed : {dele:>4}  ({len(fragments)} fragments, "
          f"{len(whole_hyphen)} hyphenated, {len(accented)} accented)")
    print(f"  add_candidate    : {add:>4}")
    print(f"  net universe change: {add - dele:+d}")
    print(f"  universe {len(universe):,} -> {len(universe) - dele + add:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
