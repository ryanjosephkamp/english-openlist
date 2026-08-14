"""
Stage 2 Report

Turns the stage 2 ledger into the number Ryan decides on.

Three things this is careful about, because each is a way to publish a
confident wrong answer:

**The rate has a denominator, and it is not 400.** Only words a dictionary
actually ruled on can say anything about the LLM. Words no source has an entry
for are *unadjudicated*, and folding them in either direction would be inventing
evidence. Coverage is therefore reported as a first-class number, not a
footnote: if most of the sample is unadjudicated, the honest conclusion is that
the method cannot answer the question.

**The sample is stratified, so the overall figure is a weighted one.** Taking
refuted/adjudicable across all 400 would badly overweight stratum 0, which is
sampled at 8.9% against 1.6% for stratum 1. The overall estimate weights each
stratum by its share of the population, and its variance carries the finite
population correction — stratum 0 samples 40 of 448, and ignoring that would
overstate the interval.

**Free Dictionary is a weaker witness.** It performs no abbreviation or proper
noun screening, so it returns "valid" for things Merriam-Webster would reject.
Every rate is therefore given twice: once as measured, and once counting only
rulings from a Merriam-Webster source.

Usage:
    python scripts/stage2_report.py
"""

import argparse
import csv
import logging
import math
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

#: Populations from the frame. Held here so the report can be recomputed from
#: the ledger alone, and asserted against the frame when it is available.
POPULATION = {"0": 448, "1": 10056, "2": 4906, "3": 2254, "4+": 2388}
TOTAL_POPULATION = sum(POPULATION.values())

STRATA = ("0", "1", "2", "3", "4+")
Z = 1.959963984540054  # 95%


def wilson(successes: int, n: int, z: float = Z) -> tuple[float, float]:
    """
    Wilson score interval.

    Used rather than the normal approximation because these denominators are
    small and the proportions may sit near 0 or 1, where the textbook interval
    runs off the end of the scale and reports impossible bounds.
    """
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def stratified_estimate(per_stratum: dict[str, tuple[int, int]]) -> tuple[float, float, float]:
    """
    Population-weighted rate and its 95% interval.

    Var = sum over strata of W_h^2 * (r_h(1-r_h)/n_h) * fpc, with the finite
    population correction fpc = (N_h - n_h)/(N_h - 1). Strata that adjudicated
    nothing contribute no estimate and are dropped from the weights, which is
    reported rather than silently absorbed.
    """
    usable = {h: (s, n) for h, (s, n) in per_stratum.items() if n > 0}
    if not usable:
        return (float("nan"), float("nan"), float("nan"))

    weight_total = sum(POPULATION[h] for h in usable)
    estimate = 0.0
    variance = 0.0

    for h, (successes, n) in usable.items():
        big_n = POPULATION[h]
        w = big_n / weight_total
        r = successes / n
        estimate += w * r
        fpc = (big_n - n) / (big_n - 1) if big_n > 1 else 0.0
        variance += (w ** 2) * (r * (1 - r) / n) * fpc

    half = Z * math.sqrt(variance)
    return (estimate, max(0.0, estimate - half), min(1.0, estimate + half))


def pct(x: float) -> str:
    return "n/a" if math.isnan(x) else f"{x * 100:.1f}%"


def summarise(rows: list[dict], mw_only: bool = False) -> dict:
    """
    Tally outcomes per stratum.

    With mw_only, a Free-Dictionary ruling is demoted to unadjudicated: the
    dictionary that answered does not screen abbreviations or proper nouns, so
    its "valid" is a weaker claim than Merriam-Webster's.
    """
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for row in rows:
        outcome = row["outcome"]
        if mw_only and outcome in ("refuted", "corroborated"):
            if not row["deciding_source"].startswith(("medical", "collegiate")):
                outcome = "unadjudicated"
        counts[row["stratum"]][outcome] += 1
        counts[row["stratum"]]["total"] += 1

    return counts


def render(rows: list[dict], mw_only: bool) -> list[str]:
    counts = summarise(rows, mw_only=mw_only)
    per_stratum: dict[str, tuple[int, int]] = {}
    lines = []

    lines.append("| Stratum | Population | Sampled | Refuted | Corroborated | Unadjudicated | Error | Error rate (95% CI) |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---|")

    for h in STRATA:
        c = counts.get(h, {})
        refuted = c.get("refuted", 0)
        corroborated = c.get("corroborated", 0)
        adjudicable = refuted + corroborated
        per_stratum[h] = (refuted, adjudicable)

        if adjudicable:
            lo, hi = wilson(refuted, adjudicable)
            cell = f"{refuted / adjudicable * 100:.1f}% ({lo * 100:.0f}–{hi * 100:.0f}%)"
        else:
            cell = "nothing adjudicable"

        lines.append(
            f"| {h} | {POPULATION[h]:,} | {c.get('total', 0)} | {refuted} | "
            f"{corroborated} | {c.get('unadjudicated', 0)} | {c.get('error', 0)} | {cell} |"
        )

    est, lo, hi = stratified_estimate(per_stratum)
    lines.append("")
    lines.append(f"**Weighted error rate across all {TOTAL_POPULATION:,} words: "
                 f"{pct(est)} (95% CI {pct(lo)} – {pct(hi)}).**")

    adjudicable_total = sum(n for _, n in per_stratum.values())
    lines.append("")
    lines.append(f"Adjudicable: **{adjudicable_total} of {len(rows)}** sampled words "
                 f"({adjudicable_total / len(rows) * 100:.1f}%). The rest had no entry "
                 f"in any source consulted, which says nothing about whether they are words.")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Report on the stage 2 sample")
    parser.add_argument("--ledger", type=Path, default=Path("corrections/ledger_stage2.csv"))
    parser.add_argument("--out", type=Path, default=Path("corrections/stage2_report.md"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    with open(args.ledger, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        logger.error("Ledger is empty; nothing to report")
        return 1

    doc: list[str] = []
    doc.append("# Stage 2 — how often was the LLM wrong?")
    doc.append("")
    doc.append(f"{len(rows)} words sampled from the {TOTAL_POPULATION:,} carrying "
               '`"status": "invalid"`, stratified by how many corpora attested them. '
               "Every one of those verdicts came from a single pass by Google Gemini 3 "
               "Flash Preview in December 2025.")
    doc.append("")
    doc.append("**No word was moved.** This stage measures.")
    doc.append("")
    doc.append("A dictionary having the word means the LLM was wrong. A dictionary *not* "
               "having it means nothing either way — much of this vocabulary is technical, "
               "and absence from Merriam-Webster is not evidence of absence from English. "
               "So the figures below are a **lower bound** on the error rate.")
    doc.append("")
    doc.append("## As measured")
    doc.append("")
    doc.extend(render(rows, mw_only=False))
    doc.append("")
    doc.append("## Counting only Merriam-Webster rulings")
    doc.append("")
    doc.append("Free Dictionary performs no abbreviation or proper-noun screening, so it "
               "returns `valid` for entries Merriam-Webster would reject. Recomputed with "
               "Free-Dictionary-only rulings demoted to unadjudicated:")
    doc.append("")
    doc.extend(render(rows, mw_only=True))
    doc.append("")

    by_source: dict[str, int] = defaultdict(int)
    for row in rows:
        by_source[row["deciding_source"] or "(none)"] += 1
    doc.append("## Which source ruled")
    doc.append("")
    doc.append("| Source | Words ruled |")
    doc.append("|---|---:|")
    for source, n in sorted(by_source.items(), key=lambda kv: -kv[1]):
        doc.append(f"| {source} | {n} |")
    doc.append("")

    degraded = sum(1 for r in rows
                   if "error" in (r["medical_status"], r["collegiate_status"], r["free_status"]))
    doc.append(f"**Lookups where at least one source errored rather than answering: "
               f"{degraded}.** An error is a statement about our quota or the network, "
               "never about the word, and is never recorded as \"not found\".")
    doc.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(doc) + "\n", encoding="utf-8")
    logger.info("Wrote %s", args.out)
    print("\n".join(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
