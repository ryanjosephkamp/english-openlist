"""
Shared machinery for the Phase 1 evidence layer.

Everything here serves one property: the evidence matrix must reproduce
byte-for-byte from sources/MANIFEST.toml alone, on a clean machine, by someone
who was not here. So every artifact is downloaded to a recorded path, hashed
before use, and every derived word set is written sorted with its own hash and
count beside it. A source whose ingest does not reproduce its declared
record_count is a hard failure, not a warning — `verify_manifest.py` enforces
that.

The pinned normalization (PROTOCOL.md §2.5, MANIFEST.toml) is implemented once,
here, and imported everywhere. Counts move with the filter, so the filter does
not get re-typed per script.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import re
import unicodedata
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCES_DIR = REPO / ".cache" / "sources"
RAW_DIR = SOURCES_DIR / "raw"
DERIVED_DIR = SOURCES_DIR / "derived"
FRAME_DIR = SOURCES_DIR / "frame"

#: The pinned form rule. `^[a-z]+$`, no length bound — D-025.
FORM_RULE = re.compile(r"[a-z]+")

#: Ingest integrity flag, NOT a form rule (PROTOCOL.md §1.3). Candidates longer
#: than this are recorded for a reason before entering the frame.
LENGTH_FLAG_OVER = 100

USER_AGENT = ("english-openlist/1.0 "
              "(https://github.com/ryanjosephkamp/english-openlist; "
              "phase 1 evidence layer)")


def normalize(raw: str) -> str | None:
    """
    The pinned normalization: NFC, casefold, accept iff ^[a-z]+$.

    Returns the normalized key, or None when the string is not form-valid.
    Applied identically to every source and to the candidate universe —
    per-source deviations (Wiktionary's lowercase-titles-only convention) are
    implemented in that source's ingest and declared in the manifest, never
    here.
    """
    s = unicodedata.normalize("NFC", raw).casefold()
    return s if FORM_RULE.fullmatch(s) else None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, *, expected_sha256: str | None = None) -> str:
    """
    Streaming download to `dest`. Returns the artifact's sha256.

    If `expected_sha256` is given and the file already exists with that hash,
    the download is skipped — that is what makes re-runs cheap and what makes
    the manifest's pin meaningful. A mismatch against a pin is a hard error:
    the artifact the manifest describes is not the artifact on the wire, and
    silently using the new one would unpin the build.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        have = sha256_file(dest)
        if expected_sha256 is None or have == expected_sha256:
            return have
        dest.unlink()  # stale partial or superseded artifact

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    h = hashlib.sha256()
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
        declared = r.headers.get("Content-Length")
        received = 0
        for chunk in iter(lambda: r.read(1 << 20), b""):
            f.write(chunk)
            h.update(chunk)
            received += len(chunk)
    # A connection that closes early looks identical to EOF in the read loop,
    # and a truncated .gz can still parse as an empty or short stream. Check
    # the byte count against the server's declaration before trusting it.
    if declared is not None and received != int(declared):
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            f"{url}: received {received:,} bytes of a declared "
            f"{int(declared):,}. Truncated download; not ingesting it.")
    tmp.rename(dest)
    got = h.hexdigest()
    if expected_sha256 is not None and got != expected_sha256:
        raise RuntimeError(
            f"{url}: sha256 {got} does not match the manifest's pin "
            f"{expected_sha256}. The pinned artifact has changed upstream; "
            "re-pin deliberately rather than ingesting whatever arrived.")
    return got


def write_derived(source_id: str, words: set[str], *, artifact_sha256: str | None,
                  url: str | None, extra: dict | None = None) -> dict:
    """
    Persist a source's normalized key set: sorted, one per line, with a meta
    JSON carrying everything the manifest and the verifier need.

    Sorted output means the derived file's own sha256 is deterministic, so a
    clean rebuild can be checked byte-for-byte, not just count-for-count.
    """
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    out = DERIVED_DIR / f"{source_id}.txt"
    with open(out, "w", encoding="utf-8") as f:
        for w in sorted(words):
            f.write(w + "\n")
    meta = {
        "source": source_id,
        "record_count": len(words),
        "derived_sha256": sha256_file(out),
        "artifact_sha256": artifact_sha256,
        "url": url,
        "retrieved": date.today().isoformat(),
        "over_length_flag": sorted(w for w in words if len(w) > LENGTH_FLAG_OVER),
    }
    if extra:
        meta.update(extra)
    with open(DERIVED_DIR / f"{source_id}.meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    return meta


def read_derived(source_id: str) -> set[str]:
    with open(DERIVED_DIR / f"{source_id}.txt", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def read_meta(source_id: str) -> dict:
    with open(DERIVED_DIR / f"{source_id}.meta.json", encoding="utf-8") as f:
        return json.load(f)


def load_frame_universe() -> set[str]:
    """The candidate universe at the pinned HF revision — strings only, no labels."""
    words: set[str] = set()
    for name in ("merged_valid_words.txt", "merged_invalid_words.txt"):
        with open(FRAME_DIR / name, encoding="utf-8") as f:
            for line in f:
                w = line.strip()
                if w:
                    words.add(w)
    return words


def open_maybe_gzip(path: Path, encoding="utf-8", errors="strict"):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding=encoding, errors=errors)
    return open(path, encoding=encoding, errors=errors)
