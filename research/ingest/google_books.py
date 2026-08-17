"""
Google Books 2020 English 1-grams — streamed, aggregated, deleted.

Why the raw shards and not the Ngram Viewer API: the shards carry
`volume_count`, the API does not, and volume-level dispersion is the only
signal left that can separate OCR noise from rare real words after §2.4 ruled
out frequency and year-spread. That measurement is also why this source is
NEVER binarised on raw frequency and never becomes a detector column: it
shares its error mode with the process that generated the candidate frame
(`frame_dependency = true`), which specification S5 models as its own latent
class rather than absorbing.

Disk discipline: one shard on disk at a time — download (~265 MB), aggregate,
delete, next. Peak disk stays near a single shard against the 16 GiB free.

Aggregation, per casefolded a-z type:
    total_match    sum of match_count over years and case variants
    total_volume   sum of volume_count over years and case variants.
                   Case variants of the same word in the same year can share
                   volumes, so this OVERCOUNTS for words with common
                   capitalised forms. It is a feature with a documented bias,
                   not a count — the manifest says so too.
    first_year / last_year
    year_count     distinct years with any occurrence (per variant, summed,
                   capped at the year span when merging)

POS-tagged rows (`school_NOUN`) fail the form rule on the underscore and drop
out on their own.

Run:  python -m research.ingest.google_books
"""

from __future__ import annotations

import gzip
import json
import sys
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .common import DERIVED_DIR, RAW_DIR, download, normalize

SHARDS = 24
URL = ("http://storage.googleapis.com/books/ngrams/books/20200217/eng/"
       "1-{i:05d}-of-00024.gz")

GB_DIR = DERIVED_DIR / "google_books"
SCHEMA = pa.schema([
    ("word", pa.string()),
    ("total_match", pa.int64()),
    ("total_volume", pa.int64()),
    ("first_year", pa.int16()),
    ("last_year", pa.int16()),
    ("year_count", pa.int16()),
])


def aggregate_shard(path: Path) -> dict[str, list]:
    agg: dict[str, list] = {}
    with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            tab = line.find("\t")
            if tab <= 0:
                continue
            key = normalize(line[:tab])
            if key is None:
                continue
            tm = tv = ny = 0
            fy, ly = 9999, 0
            # year,match,volume triples, tab-separated
            for triple in line[tab + 1:].split("\t"):
                parts = triple.split(",")
                if len(parts) != 3:
                    continue
                try:
                    y, m, v = int(parts[0]), int(parts[1]), int(parts[2])
                except ValueError:
                    continue
                tm += m
                tv += v
                ny += 1
                if y < fy:
                    fy = y
                if y > ly:
                    ly = y
            if tm == 0:
                continue
            row = agg.get(key)
            if row is None:
                agg[key] = [tm, tv, fy, ly, ny]
            else:
                row[0] += tm
                row[1] += tv
                if fy < row[2]:
                    row[2] = fy
                if ly > row[3]:
                    row[3] = ly
                row[4] += ny
    return agg


def write_shard_parquet(agg: dict[str, list], out: Path) -> None:
    words = sorted(agg)
    cols = list(zip(*(agg[w] for w in words))) if words else [[]] * 5
    table = pa.table({
        "word": words,
        "total_match": list(cols[0]) if words else [],
        "total_volume": list(cols[1]) if words else [],
        "first_year": list(cols[2]) if words else [],
        "last_year": list(cols[3]) if words else [],
        "year_count": list(cols[4]) if words else [],
    }, schema=SCHEMA)
    pq.write_table(table, out, compression="zstd")


def merge_shards() -> Path:
    """24 shard parquets -> one aggregate. Shards are alphabetical ranges, so
    cross-shard duplicates are rare; the groupby handles the boundary cases."""
    import pandas as pd
    frames = [pq.read_table(GB_DIR / f"shard-{i:05d}.parquet").to_pandas()
              for i in range(SHARDS)]
    df = pd.concat(frames, ignore_index=True)
    del frames
    g = df.groupby("word", sort=True).agg(
        total_match=("total_match", "sum"),
        total_volume=("total_volume", "sum"),
        first_year=("first_year", "min"),
        last_year=("last_year", "max"),
        year_count=("year_count", "sum"),
    ).reset_index()
    # summed year_count across case variants can exceed the span; cap it there
    span = (g["last_year"] - g["first_year"] + 1).clip(lower=1)
    g["year_count"] = g["year_count"].clip(upper=span)
    out = DERIVED_DIR / "google_books_1grams.parquet"
    pq.write_table(pa.Table.from_pandas(g, preserve_index=False), out,
                   compression="zstd")
    return out


def main() -> int:
    GB_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    for i in range(SHARDS):
        out = GB_DIR / f"shard-{i:05d}.parquet"
        if out.exists():
            print(f"[gb] shard {i:02d}: parquet exists, skipping", flush=True)
            continue
        url = URL.format(i=i)
        raw = RAW_DIR / f"gb-1-{i:05d}.gz"
        t1 = time.time()
        # One retry per shard: a 265 MB transfer that fails once mid-stream
        # should not sink a four-hour run.
        try:
            sha = download(url, raw)
        except Exception as e:
            print(f"[gb] shard {i:02d}: download failed ({e}); retrying once",
                  flush=True)
            time.sleep(10)
            sha = download(url, raw)
        t2 = time.time()
        agg = aggregate_shard(raw)
        write_shard_parquet(agg, out)
        raw.unlink()  # one shard on disk at a time
        # meta appended per shard so a resumed run still knows every hash
        with open(GB_DIR / "shards.jsonl", "a", encoding="utf-8") as mf:
            mf.write(json.dumps({"shard": i, "sha256": sha,
                                 "types": len(agg)}) + "\n")
        print(f"[gb] shard {i:02d}: {len(agg):>9,} a-z types | "
              f"dl {t2-t1:5.0f}s parse {time.time()-t2:5.0f}s | "
              f"elapsed {(time.time()-t0)/60:5.1f}m", flush=True)
        del agg

    out = merge_shards()
    n = pq.read_metadata(out).num_rows
    shard_meta = []
    with open(GB_DIR / "shards.jsonl", encoding="utf-8") as mf:
        seen = {}
        for line in mf:
            rec = json.loads(line)
            seen[rec["shard"]] = rec       # last write per shard wins
        shard_meta = [seen[k] for k in sorted(seen)]
    with open(DERIVED_DIR / "google_books.meta.json", "w", encoding="utf-8") as f:
        json.dump({"source": "google_books_1gram_eng_2020",
                   "record_count": n,
                   "shards": shard_meta,
                   "aggregate": str(out.name)}, f, indent=2)
    print(f"[gb] DONE: {n:,} distinct a-z types in {(time.time()-t0)/60:.1f}m",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
