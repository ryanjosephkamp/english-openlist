"""
Assemble the evidence matrix.

Frame (D-026 as scoped by D-030): the candidate universe at the pinned HF
revision, unioned with the form-valid key set of every BINARY detector source.
Corpus sources join as feature columns over that frame and contribute no
members.

Output: research/data/evidence.parquet — one row per frame word:

    word                    the normalized key
    in_universe             inherited member at the pinned revision
    wordnet .. csw21        one bool per binary detector
    scowl_tier              int16 ordinal, 0 = absent, else the smallest tier
    wikt_title_screen       bool — ANY-language spelling exists (a screen, not
                            a detector; `agiler` is the reminder)
    wordfreq_zipf           float32, NaN when wordfreq does not list the word
    gb_total_match          int64, 0 when Google Books never saw it
    gb_total_volume         int64
    gb_first_year           int16, 0 when absent
    gb_last_year            int16, 0 when absent
    gb_year_count           int16, 0 when absent

Also writes research/data/frame_contributions.json — the per-source answer to
D-026's "record how many candidates each source adds".

Run:  python -m research.ingest.build_evidence
"""

from __future__ import annotations

import json
import sys
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .common import DERIVED_DIR, REPO, load_frame_universe, read_derived, read_meta

OUT_DIR = REPO / "research" / "data"

#: Binary detector sources, in the column order the matrix carries. These are
#: also exactly the frame contributors — D-030.
BINARY_SOURCES = [
    "wordnet", "wiktionary_english", "web2",
    "hunspell_en_US", "hunspell_en_GB", "hunspell_en_CA", "hunspell_en_AU",
    "enable1", "sowpods_legacy", "nwl2023", "csw21",
]


def main() -> int:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    universe = load_frame_universe()
    print(f"[evidence] universe at pinned revision : {len(universe):>10,}", flush=True)

    sets: dict[str, set[str]] = {}
    contributions = {}
    frame = set(universe)
    for src in BINARY_SOURCES + ["scowl"]:
        s = read_derived(src)
        sets[src] = s
        solo = len(s - universe)
        before = len(frame)
        frame |= s
        contributions[src] = {
            "keys": len(s),
            "absent_from_universe": solo,
            "new_to_frame_in_order": len(frame) - before,
        }
        print(f"[evidence] {src:20s} {len(s):>9,} keys | adds alone "
              f"{solo:>7,} | new in union order {len(frame)-before:>7,}",
              flush=True)

    print(f"[evidence] FRAME: {len(frame):,} "
          f"(universe {len(universe):,} + {len(frame)-len(universe):,} from sources)",
          flush=True)

    words = sorted(frame)
    n = len(words)
    cols: dict[str, object] = {"word": words,
                               "in_universe": [w in universe for w in words]}
    del universe

    for src in BINARY_SOURCES:
        s = sets[src]
        cols[src] = [w in s for w in words]

    # SCOWL: one ordinal, never ten binaries (D-021)
    tiers: dict[str, int] = {}
    with open(DERIVED_DIR / "scowl_tiers.tsv", encoding="utf-8") as f:
        for line in f:
            w, t = line.rstrip("\n").split("\t")
            tiers[w] = int(t)
    cols["scowl_tier"] = np.array([tiers.get(w, 0) for w in words], dtype=np.int16)
    del tiers

    screen = read_derived("wiktionary_titles")
    cols["wikt_title_screen"] = [w in screen for w in words]
    del screen

    zipf: dict[str, float] = {}
    with open(DERIVED_DIR / "wordfreq_zipf.tsv", encoding="utf-8") as f:
        for line in f:
            w, z = line.rstrip("\n").split("\t")
            zipf[w] = float(z)
    cols["wordfreq_zipf"] = np.array([zipf.get(w, np.nan) for w in words],
                                     dtype=np.float32)
    del zipf
    del sets

    # Google Books aggregates — a dict-free merge keyed on the sorted order
    gb = pq.read_table(DERIVED_DIR / "google_books_1grams.parquet")
    gb_words = gb.column("word").to_pylist()
    idx = {w: i for i, w in enumerate(gb_words)}
    del gb_words
    gb_cols = {name: gb.column(name).to_numpy() for name in
               ("total_match", "total_volume", "first_year", "last_year",
                "year_count")}
    del gb
    hit = 0
    for name, dtype in (("total_match", np.int64), ("total_volume", np.int64),
                        ("first_year", np.int16), ("last_year", np.int16),
                        ("year_count", np.int16)):
        src_arr = gb_cols[name]
        out = np.zeros(n, dtype=dtype)
        for i, w in enumerate(words):
            j = idx.get(w)
            if j is not None:
                out[i] = src_arr[j]
        cols[f"gb_{name}"] = out
    hit = sum(1 for w in words if w in idx)
    gb_total_types = len(idx)
    del idx, gb_cols

    table = pa.table(cols)
    out_path = OUT_DIR / "evidence.parquet"
    pq.write_table(table, out_path, compression="zstd")

    meta = {
        "frame_size": n,
        "universe_size": int(sum(cols["in_universe"])),
        "contributed_by_sources": n - int(sum(cols["in_universe"])),
        "gb_types_total": gb_total_types,
        "gb_types_in_frame": hit,
        "gb_types_declined_by_frame": gb_total_types - hit,   # D-030's visible cost
        "contributions": contributions,
        "columns": table.column_names,
        "wiktionary_english_count": read_meta("wiktionary_english")["record_count"],
    }
    with open(OUT_DIR / "frame_contributions.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"[evidence] gb coverage of frame: {hit:,}/{n:,} "
          f"({100*hit/n:.2f}%) | gb types declined by frame: "
          f"{gb_total_types-hit:,}", flush=True)
    print(f"[evidence] wrote {out_path} "
          f"({out_path.stat().st_size/1e6:.1f} MB) in {time.time()-t0:.0f}s",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
