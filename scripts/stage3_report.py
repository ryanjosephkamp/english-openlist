"""
Stage 3 Report

Turns the stage 3 ledger into a statement about the 16,478 synthetic
comparatives and superlatives.

The question each row answers is narrow and checkable: does Merriam-Webster list
this comparative among the inflections of its stem? MW records those in
`meta.stems`, so a "no" here is the dictionary enumerating a word's forms and
not including this one — which is much stronger evidence than a headword lookup
returning "not found".

Coverage is reported first and per stratum, because it is the number that says
whether the rest means anything. Stage 2 was abandoned on exactly this: it could
rule on 4.5% of its sample, and no rate computed from that is worth acting on.

Usage:
    python scripts/stage3_report.py
"""

import argparse
import csv
import logging
import math
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

#: Stems and forms per stratum, from corrections/stage3_frame.csv.
POPULATION = {"wn-adj": 1_717, "wn-other": 306, "not-in-wn": 6_786}
FORMS = {"wn-adj": 3_166, "wn-other": 424, "not-in-wn": 12_888}
STRATA = ("wn-adj", "wn-other", "not-in-wn")
TOTAL_STEMS = sum(POPULATION.values())
TOTAL_FORMS = sum(FORMS.values())
Z = 1.959963984540054

LABEL = {
    "wn-adj": "WordNet adjective",
    "wn-other": "WordNet noun/verb only",
    "not-in-wn": "not in WordNet",
}


def wilson(successes: int, n: int, z: float = Z) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def tally(rows: list[dict]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        counts[row["stratum"]][row["outcome"]] += 1
        counts[row["stratum"]]["n"] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Report on the stage 3 sample")
    parser.add_argument("--ledger", type=Path, default=Path("corrections/ledger_stage3.csv"))
    parser.add_argument("--out", type=Path, default=Path("corrections/stage3_report.md"))
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")

    with open(args.ledger, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        logger.error("Ledger is empty")
        return 1

    counts = tally(rows)
    doc: list[str] = []

    doc.append("# Stage 3 — are the synthetic comparatives real?")
    doc.append("")
    doc.append(f"{len(rows)} stems sampled from the {TOTAL_STEMS:,} behind the "
               f"{TOTAL_FORMS:,} synthetic `-er`/`-est` forms in the valid list — "
               "words like `abacteremicer`, `abambulacralest` and `abatabler`.")
    doc.append("")
    doc.append("**No word was moved.** This stage measures.")
    doc.append("")
    doc.append("The question is not whether Merriam-Webster carries the comparative as "
               "a headword — it never would. It is whether MW lists the comparative "
               "among the inflections of its stem, in `meta.stems`. A \"no\" there is "
               "the dictionary enumerating a word's forms and leaving this one out.")
    doc.append("")

    doc.append("## Coverage — can the question be answered at all?")
    doc.append("")
    doc.append("| Stratum | Stems | Sampled | MW ruled | Coverage |")
    doc.append("|---|---:|---:|---:|---:|")
    ruled_total = 0
    for h in STRATA:
        c = counts.get(h, {})
        n = c.get("n", 0)
        ruled = c.get("inflection-listed", 0) + c.get("inflection-absent", 0)
        ruled_total += ruled
        cov = f"{ruled / n * 100:.1f}%" if n else "n/a"
        doc.append(f"| {LABEL[h]} | {POPULATION[h]:,} | {n} | {ruled} | {cov} |")
    doc.append(f"| **Total** | **{TOTAL_STEMS:,}** | **{len(rows)}** | "
               f"**{ruled_total}** | **{ruled_total / len(rows) * 100:.1f}%** |")
    doc.append("")
    doc.append(f"Merriam-Webster could rule on **{ruled_total} of {len(rows)}** stems. "
               "For comparison, stage 2 managed 4.5% and was abandoned on that basis. "
               "This one can be answered.")
    doc.append("")

    doc.append("## The result")
    doc.append("")
    doc.append("| Stratum | MW ruled | Comparative recognised | Not recognised | Rate (95% CI) |")
    doc.append("|---|---:|---:|---:|---|")
    listed_total = 0
    for h in STRATA:
        c = counts.get(h, {})
        listed = c.get("inflection-listed", 0)
        absent = c.get("inflection-absent", 0)
        ruled = listed + absent
        listed_total += listed
        if ruled:
            lo, hi = wilson(listed, ruled)
            cell = f"{listed / ruled * 100:.1f}% ({lo * 100:.1f}–{hi * 100:.1f}%)"
        else:
            cell = "nothing rulable"
        doc.append(f"| {LABEL[h]} | {ruled} | {listed} | {absent} | {cell} |")

    lo, hi = wilson(listed_total, ruled_total)
    doc.append(f"| **Total** | **{ruled_total}** | **{listed_total}** | "
               f"**{ruled_total - listed_total}** | "
               f"**{listed_total / ruled_total * 100:.1f}% "
               f"({lo * 100:.1f}–{hi * 100:.1f}%)** |")
    doc.append("")
    doc.append(f"**Of {ruled_total} stems Merriam-Webster could rule on, it recognises "
               f"the comparative for {listed_total}.**")
    doc.append("")

    # Population-weighted, over rulable stems only, and said to be that.
    estimate = 0.0
    for h in STRATA:
        c = counts.get(h, {})
        ruled = c.get("inflection-listed", 0) + c.get("inflection-absent", 0)
        if ruled:
            estimate += (POPULATION[h] / TOTAL_STEMS) * (c.get("inflection-listed", 0) / ruled)
    doc.append(f"Weighting each stratum by its share of the {TOTAL_STEMS:,} stems gives "
               f"**{estimate * 100:.2f}%** — on the order of {round(estimate * TOTAL_STEMS)} "
               f"stems, and perhaps {round(estimate * TOTAL_FORMS)} of the "
               f"{TOTAL_FORMS:,} forms, that a dictionary would accept.")
    doc.append("")
    doc.append("That extrapolation assumes the stems MW could not rule on behave like "
               "those it could, within their stratum. It is least safe for *not in "
               "WordNet*, where coverage is lowest — but those are also the most "
               "obscure stems, so if the assumption fails it most likely flatters the "
               "generator rather than the reverse.")
    doc.append("")

    listed_rows = [r for r in rows if r["outcome"] == "inflection-listed"]
    if listed_rows:
        doc.append("## What it got right")
        doc.append("")
        for r in listed_rows:
            doc.append(f"- **`{r['stem']}`** → `{r['forms_listed']}` — "
                       f"MW lists these among its inflections.")
        doc.append("")
        doc.append("A real gradable adjective, produced by the same blind affixation "
                   "that produced the rest. The generator was not right on purpose.")
        doc.append("")

    doc.append("## What it got wrong")
    doc.append("")
    doc.append("MW enumerates each stem's real inflections and simply does not include "
               "the comparative:")
    doc.append("")
    doc.append("| Stem | Synthetic forms | What MW actually lists |")
    doc.append("|---|---|---|")
    shown = 0
    for r in rows:
        if r["outcome"] == "inflection-absent" and r["mw_stems"] and shown < 8:
            doc.append(f"| `{r['stem']}` | `{r['forms']}` | {r['mw_stems'][:70]} |")
            shown += 1
    doc.append("")

    no_stems = sum(1 for r in rows if r["outcome"] == "no-stems-array")
    errors = sum(1 for r in rows if r["outcome"] == "error")
    if no_stems or errors:
        doc.append(f"Excluded: {no_stems} ruled by a source with no inflection list "
                   f"(Free Dictionary), {errors} lookup errors. Neither counts as an answer.")
        doc.append("")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(doc) + "\n", encoding="utf-8")
    logger.info("Wrote %s", args.out)
    print("\n".join(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
