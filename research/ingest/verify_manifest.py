"""
The reproducibility gate: a source whose ingest does not reproduce its declared
record_count is a hard failure, not a warning.

This re-derives nothing. It checks that what the manifest declares, what each
ingest's meta recorded, and what is actually on disk agree with one another:

  * manifest record_count == meta record_count == a fresh line count of the
    derived file
  * manifest sha256 (when pinned) == meta artifact_sha256
  * the derived file's own sha256 == the meta's derived_sha256 (byte-level
    reproducibility, not just count-level)
  * the manifest's pinned normalization string matches the implementation

Run:  python -m research.ingest.verify_manifest        (exit 1 on any mismatch)
"""

from __future__ import annotations

import sys
import tomllib

from .common import DERIVED_DIR, REPO, read_meta, sha256_file

CANONICAL_NORMALIZATION = "NFC; casefold; accept iff ^[a-z]+$"

failures: list[str] = []


def check(cond: bool, label: str) -> None:
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
    if not cond:
        failures.append(label)


def main() -> int:
    with open(REPO / "sources" / "MANIFEST.toml", "rb") as f:
        manifest = tomllib.load(f)

    print("=== normalization pin ===")
    check(manifest["manifest"]["normalization"] == CANONICAL_NORMALIZATION,
          "manifest normalization matches the implementation's canonical string")

    print("=== per-source: manifest == meta == disk ===")
    for src in manifest.get("source", []):
        sid = src["id"]
        declared = src.get("record_count", 0)
        if not declared:
            print(f"  --    {sid}: no declared record_count yet, skipping")
            continue
        try:
            meta = read_meta(sid)
        except FileNotFoundError:
            check(False, f"{sid}: declared in manifest but never ingested")
            continue
        check(meta["record_count"] == declared,
              f"{sid}: meta count {meta['record_count']:,} == manifest {declared:,}")
        derived = DERIVED_DIR / f"{sid}.txt"
        n = sum(1 for line in open(derived, encoding="utf-8") if line.strip())
        check(n == declared, f"{sid}: fresh line count {n:,} == manifest {declared:,}")
        check(sha256_file(derived) == meta["derived_sha256"],
              f"{sid}: derived file byte-identical to its recorded hash")
        pinned = src.get("sha256", "")
        if pinned and meta.get("artifact_sha256"):
            check(meta["artifact_sha256"] == pinned,
                  f"{sid}: artifact sha256 matches the manifest pin")

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S) — the build does not reproduce")
        return 1
    print("MANIFEST VERIFIED — every declared count reproduces")
    return 0


if __name__ == "__main__":
    sys.exit(main())
