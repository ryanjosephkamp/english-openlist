"""
Build a practice deck for hardening the adjudication app.

NOT the calibration sample — that is drawn in Phase 4, stratified by posterior
decile, after the model exists. This deck exists so the app's append-only log,
replay-resume and blinding can be exercised and trusted before any real
adjudication minute is spent in it.

Selection is by sha256(seed:word) ranking over the frame — the project's
determinism rule — so the deck reproduces exactly on any machine.

Run:  python -m research.adjudicate.make_practice_deck --n 24
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research.ingest.common import load_frame_universe  # noqa: E402

HERE = Path(__file__).resolve().parent
SEED = "practice-deck-2026-08-17"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--out", type=Path, default=HERE / "decks" / "practice.jsonl")
    args = ap.parse_args()

    frame = load_frame_universe()
    ranked = sorted(frame,
                    key=lambda w: hashlib.sha256(f"{SEED}:{w}".encode()).hexdigest())
    picked = ranked[: args.n]

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for i, w in enumerate(picked):
            f.write(json.dumps({"id": f"practice-{i:04d}", "word": w,
                                "kind": "practice"}) + "\n")
    print(f"wrote {args.out} — {len(picked)} items, seed {SEED!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
