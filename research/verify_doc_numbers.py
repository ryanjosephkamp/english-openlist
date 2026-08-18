"""
PROTOCOL §9, mechanism 1 — implemented at last.

    "Every number comes from code. No figure appears in any document unless a
     committed script produced it and can regenerate it. Enforced by a check
     that re-derives the numbers quoted in markdown and fails on mismatch."

That check is this file. It was specified in Phase 0 and not built until a
status review found fifteen documentation defects — every one of them exactly
the drift this mechanism was designed to catch (D-033).

Three kinds of assertion:

  REQUIRED   a figure re-derived from the pinned data must appear, formatted
             exactly, in the named documents. If the data moves, the derivation
             moves, the assertion fails, and the document has to be updated
             consciously.
  FORBIDDEN  superseded figures that must NOT appear in PROTOCOL.md. They are
             deliberately NOT forbidden in research/DECISIONS.md (append-only,
             dated, historical) or CLAUDE.md (which explains superseded figures
             by design). PROTOCOL.md describes the present; history lives in
             the decision log.
  LABELLED   the one historical measurement PROTOCOL keeps — the Phase 0
             three-detector table in §3.4 — must carry its supersession label.

Scope note: figures that only a full evidence.parquet scan can re-derive (the
SR2 strata) are checked against research/phase2_gate.json + SR2_REPORT.md,
which the gate module regenerates from the parquet; re-deriving 9.79M rows on
every pytest run would make the suite too slow to run reflexively, and a check
nobody runs catches nothing.

Run:  python -m research.verify_doc_numbers      (exit 1 on any failure)
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FRAME = REPO / ".cache" / "sources" / "frame"
DERIVED = REPO / ".cache" / "sources" / "derived"


def data_available() -> bool:
    return (FRAME / "merged_valid_words.txt").exists() and DERIVED.exists()


def _count(path: Path) -> int:
    with open(path, encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def _derived_count(source_id: str) -> int:
    with open(DERIVED / f"{source_id}.meta.json", encoding="utf-8") as f:
        return json.load(f)["record_count"]


def derive_figures() -> dict[str, tuple[str, list[str]]]:
    """label -> (exact formatted string, documents it must appear in)."""
    valid = {w.strip() for w in open(FRAME / "merged_valid_words.txt", encoding="utf-8")}
    invalid_n = _count(FRAME / "merged_invalid_words.txt")
    universe_n = len(valid) + invalid_n            # verified disjoint at ingest
    wordnet = {w.strip() for w in open(DERIVED / "wordnet.txt", encoding="utf-8")}

    mw_forms: set[str] = set()
    for name in ("ledger_stage3.csv", "ledger_stage4.csv"):
        with open(REPO / "corrections" / name, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("outcome") == "inflection-absent":
                    mw_forms.update(row.get("forms_missing", "").split())

    fc = json.load(open(REPO / "research" / "frame_contributions.json", encoding="utf-8"))
    gate = json.load(open(REPO / "research" / "phase2_gate.json", encoding="utf-8"))
    sr2 = (REPO / "research" / "SR2_REPORT.md").read_text(encoding="utf-8")
    # the gate module re-derives these from evidence.parquet; here we assert the
    # documents agree with the regenerable reports
    m = re.search(r"\| all-zero on every detector \| ([\d,]+)", sr2)
    all_zero = m.group(1) if m else "MISSING"
    m = re.search(r"\*\*no evidence of any kind\*\* \| \*\*([\d,]+)\*\*", sr2)
    no_ev = m.group(1) if m else "MISSING"

    P, C = "PROTOCOL.md", "CLAUDE.md"
    return {
        "valid at pin":        (f"{len(valid):,}", [P, C]),
        "invalid at pin":      (f"{invalid_n:,}", [P, C]),
        "universe at pin":     (f"{universe_n:,}", [P, C]),
        "wordnet keys":        (f"{len(wordnet):,}", [P, C]),
        "valid ∩ wordnet":     (f"{len(valid & wordnet):,}", [P, C]),
        "wiktionary titles":   (f"{_derived_count('wiktionary_titles'):,}", [P, C]),
        "wiktionary english":  (f"{_derived_count('wiktionary_english'):,}", [P, C]),
        "web2 keys":           (f"{_derived_count('web2'):,}", [P, C]),
        "frame size":          (f"{fc['frame_size']:,}", [P]),
        "frame contribution":  (f"{fc['contributed_by_sources']:,}", [P]),
        "mw-refuted forms":    (f"{len(mw_forms)}", [P]),
        "sr2 all-zero":        (all_zero, [P]),
        "sr2 no-evidence":     (no_ev, [P]),
        "sr3 verdict":         ("passes" if not gate["sr3_fires"] else "FIRES", []),
    }


#: Superseded figures with no remaining claim to currency in PROTOCOL.md.
#: History lives in DECISIONS.md (append-only) and CLAUDE.md's delta explainers.
FORBIDDEN_IN_PROTOCOL = [
    "345,297", "9,308,855", "9,654,152", "9,653,962",
    "77,477", "4,416,714", "234,428", "57,977", "57,967",
]

#: §3.4 keeps the Phase 0 three-detector measurement as design motivation; it
#: may stay only while explicitly labelled as superseded.
HISTORICAL_LABEL = "superseded by the post-ingest measurement"


def main() -> int:
    if not data_available():
        print("data not present (.cache/sources); nothing to verify against")
        return 0

    figures = derive_figures()
    docs = {name: (REPO / name).read_text(encoding="utf-8")
            for name in ("PROTOCOL.md", "CLAUDE.md")}
    failures: list[str] = []

    print("=== REQUIRED: derived figures present, formatted exactly ===")
    for label, (value, targets) in figures.items():
        for doc in targets:
            ok = value in docs[doc]
            print(f"  {'ok  ' if ok else 'FAIL'}  {doc:12s} contains {value:>12s}  ({label})")
            if not ok:
                failures.append(f"{doc}: missing {value} ({label})")

    print("=== FORBIDDEN: superseded figures absent from PROTOCOL.md ===")
    for s in FORBIDDEN_IN_PROTOCOL:
        n = docs["PROTOCOL.md"].count(s)
        print(f"  {'ok  ' if n == 0 else 'FAIL'}  {s:12s} occurs {n}x")
        if n:
            failures.append(f"PROTOCOL.md: superseded figure {s} present x{n}")

    print("=== LABELLED: the §3.4 historical table carries its supersession label ===")
    proto = docs["PROTOCOL.md"]
    if "8,261,454" in proto:
        ok = HISTORICAL_LABEL in proto
        print(f"  {'ok  ' if ok else 'FAIL'}  historical table labelled")
        if not ok:
            failures.append("PROTOCOL.md: §3.4 historical figures present without label")
    else:
        print("  --    historical table absent; nothing to label")

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S) — a document quotes a figure the data does not support:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("DOC NUMBERS VERIFIED — every quoted figure re-derives")
    return 0


if __name__ == "__main__":
    sys.exit(main())
