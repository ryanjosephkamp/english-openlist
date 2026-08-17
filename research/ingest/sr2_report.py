"""
Stopping rule SR2, measured.

SR2 (PROTOCOL.md §7): after full ingest, no single evidence pattern may hold
more than 50% of the candidate frame — above that, the majority of the
population shares one posterior and per-word probabilities are not a meaningful
output.

The rule was written when "evidence" meant binary detector patterns. The corpus
arm complicates the reading, so this reports BOTH, labelled, and argues
neither:

  Reading A — binary detectors only. The pattern is the tuple of the eleven
  detector columns plus scowl-presence. Two words with the same pattern get
  the same posterior under S1–S3, which is the sharing SR2 forbids.

  Reading B — with the corpus arm. Under S4/S5 the continuous features
  (wordfreq zipf, GB match/volume/years) differentiate within a binary
  pattern, so the undifferentiated mass is the set of words with an all-zero
  binary pattern AND no corpus data at all. That is the cell where the model
  genuinely has nothing.

Output: research/SR2_REPORT.md, plus the verdict on stdout.

Run:  python -m research.ingest.sr2_report
"""

from __future__ import annotations

import sys
from collections import Counter
from datetime import date

import numpy as np
import pyarrow.parquet as pq

from .build_evidence import BINARY_SOURCES, OUT_DIR

THRESHOLD = 0.50


def main() -> int:
    t = pq.read_table(OUT_DIR / "evidence.parquet")
    n = t.num_rows

    det = {s: t.column(s).to_numpy(zero_copy_only=False) for s in BINARY_SOURCES}
    det["scowl"] = t.column("scowl_tier").to_numpy() > 0
    names = BINARY_SOURCES + ["scowl"]

    # pattern id per row, vectorised: bit i set = detector i fired
    pattern = np.zeros(n, dtype=np.int64)
    for i, s in enumerate(names):
        pattern |= det[s].astype(np.int64) << i

    counts = Counter(pattern.tolist())
    total_patterns = len(counts)
    biggest_id, biggest_n = counts.most_common(1)[0]

    has_gb = t.column("gb_total_match").to_numpy() > 0
    has_wf = ~np.isnan(t.column("wordfreq_zipf").to_numpy(zero_copy_only=False))
    all_zero = pattern == 0
    no_evidence = all_zero & ~has_gb & ~has_wf

    a_share = biggest_n / n
    b_share = int(no_evidence.sum()) / n
    a_fires = a_share > THRESHOLD
    b_fires = b_share > THRESHOLD

    def bits(pid: int) -> str:
        on = [names[i] for i in range(len(names)) if pid >> i & 1]
        return "all-zero" if not on else "+".join(on)

    lines = []
    lines.append("# SR2 — the all-zero stratum after full ingest\n")
    lines.append(f"Measured {date.today().isoformat()} over the assembled "
                 f"evidence matrix: **{n:,} frame words**, "
                 f"{total_patterns:,} distinct binary evidence patterns.\n")
    lines.append("## Reading A — binary detector patterns (S1–S3 posteriors)\n")
    lines.append("| Pattern | Words | Share |\n|---|---:|---:|")
    for pid, c in counts.most_common(12):
        lines.append(f"| `{bits(pid)}` | {c:,} | {100*c/n:.2f}% |")
    lines.append(f"\nBiggest cell: `{bits(biggest_id)}` at **{100*a_share:.2f}%** "
                 f"against the 50% threshold — SR2 under this reading "
                 f"**{'FIRES' if a_fires else 'passes'}**.\n")
    lines.append("## Reading B — undifferentiated after the corpus arm (S4/S5)\n")
    lines.append(f"| Stratum | Words | Share |\n|---|---:|---:|")
    lines.append(f"| all-zero on every detector | {int(all_zero.sum()):,} "
                 f"| {100*int(all_zero.sum())/n:.2f}% |")
    lines.append(f"| …of which Google Books has data | "
                 f"{int((all_zero & has_gb).sum()):,} | "
                 f"{100*int((all_zero & has_gb).sum())/n:.2f}% |")
    lines.append(f"| …of which wordfreq has data | "
                 f"{int((all_zero & has_wf).sum()):,} | "
                 f"{100*int((all_zero & has_wf).sum())/n:.2f}% |")
    lines.append(f"| **no evidence of any kind** | **{int(no_evidence.sum()):,}** "
                 f"| **{100*b_share:.2f}%** |")
    lines.append(f"\nUndifferentiated share: **{100*b_share:.2f}%** against the "
                 f"50% threshold — SR2 under this reading "
                 f"**{'FIRES' if b_fires else 'passes'}**.\n")
    lines.append("## The verdict belongs to the protocol's owner\n")
    lines.append(
        "Reading A is the rule as written; reading B is the rule as "
        "motivated (\"the majority of the population shares one posterior\"). "
        "Under S1–S3 the binary pattern IS the posterior's whole input, so "
        "reading A is the honest bound for those specifications; under S4/S5 "
        "the corpus features differentiate within a pattern, and reading B "
        "measures what even they cannot reach. Neither reading is argued away "
        "here — the phase halts at this report either way, and which reading "
        "governs is recorded as a decision before Phase 2 proceeds.\n")

    out = OUT_DIR.parent / "SR2_REPORT.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"reading A: biggest binary pattern {100*a_share:.2f}% -> "
          f"{'FIRES' if a_fires else 'passes'}")
    print(f"reading B: no-evidence share      {100*b_share:.2f}% -> "
          f"{'FIRES' if b_fires else 'passes'}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
