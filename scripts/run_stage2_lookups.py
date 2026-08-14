"""
Stage 2 Lookup Runner

Looks up the 400 sampled words and records what each dictionary said.

**This script moves nothing.** It reads the sample, calls dictionaries, and
writes a ledger. It never opens the word lists, let alone writes them.

What it is measuring: 20,052 words in the valid list carry `"status": "invalid"`
because one LLM pass said so in December 2025. How often was that wrong?

The answer can only ever be a *lower bound*, and the outcome vocabulary is built
to keep that honest:

    refuted        a dictionary has the word as a word -> the LLM was wrong
    corroborated   a dictionary has it as an abbreviation or proper noun, which
                   this dataset excludes -> the LLM's call was defensible
    unadjudicated  no dictionary has an entry -> nothing follows. Much of this
                   vocabulary is technical, and absence from Merriam-Webster is
                   not evidence a word does not exist.
    error          every source failed. Excluded from the rate and counted
                   separately, because a quota failure is not a verdict.

Sources are consulted Medical, then Collegiate, then Free Dictionary. Medical
leads because its quota is unspent while the nightly run consumes Collegiate's
entirely, and because this vocabulary is heavily medical and chemical.

Usage:
    python scripts/run_stage2_lookups.py --dry-run
    EOL_DICT_CACHE=1 python scripts/run_stage2_lookups.py
"""

import argparse
import asyncio
import csv
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.dictionary_api import DictionaryAPIClient, WordStatus, cache_enabled

logger = logging.getLogger(__name__)

#: Medical first. See the module docstring.
LOOKUP_ORDER = ("medical", "collegiate", "free")

LEDGER_FIELDS = [
    "word",
    "stage",
    "stratum",
    "gemini_verdict",
    "outcome",
    "action",
    "deciding_source",
    "deciding_status",
    "medical_status",
    "collegiate_status",
    "free_status",
    "part_of_speech",
    "definition",
    "decided_date",
]

REFUTES = {WordStatus.VALID.value}
CORROBORATES = {WordStatus.ABBREVIATION.value, WordStatus.PROPER_NOUN.value}


def classify(statuses: dict, deciding_status: str | None) -> str:
    """Turn what the sources said into one of the four outcomes."""
    if deciding_status in REFUTES:
        return "refuted"
    if deciding_status in CORROBORATES:
        return "corroborated"

    consulted = [s for s in statuses.values() if s not in ("unconfigured",)]
    if consulted and all(s == WordStatus.ERROR.value for s in consulted):
        return "error"
    if any(s == WordStatus.NOT_FOUND.value for s in consulted):
        # At least one source genuinely answered "no entry". Errors alongside
        # that are noted in the per-source columns rather than hidden.
        return "unadjudicated"
    return "error"


async def look_up_all(sample: list[dict], decided: str) -> list[dict]:
    client = DictionaryAPIClient()
    rows = []

    for i, entry in enumerate(sample, 1):
        word = entry["word"]
        found = await client.lookup_all(word, order=LOOKUP_ORDER)

        statuses = found["statuses"]
        result = found["result"]
        deciding_status = result.status.value if result else None
        outcome = classify(statuses, deciding_status)

        rows.append({
            "word": word,
            "stage": "2",
            "stratum": entry["stratum"],
            "gemini_verdict": "invalid",
            "outcome": outcome,
            # Stage 2 measures. It does not move words, and the ledger says so
            # on every single row.
            "action": "none",
            "deciding_source": found["deciding_source"] or "",
            "deciding_status": deciding_status or "",
            "medical_status": statuses.get("medical", ""),
            "collegiate_status": statuses.get("collegiate", ""),
            "free_status": statuses.get("free", ""),
            "part_of_speech": (result.part_of_speech if result else "") or "",
            "definition": ((result.definition if result else "") or "").replace("\n", " ")[:300],
            "decided_date": decided,
        })

        if i % 25 == 0 or i == len(sample):
            logger.info("  %d/%d looked up", i, len(sample))

    logger.info("Cache: collegiate %d hits / %d misses, medical %d/%d, free %d/%d",
                client.mw.cache.hits, client.mw.cache.misses,
                client.mw_medical.cache.hits if client.mw_medical else 0,
                client.mw_medical.cache.misses if client.mw_medical else 0,
                client.free_dict.cache.hits, client.free_dict.cache.misses)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the stage 2 lookups")
    parser.add_argument("--sample", type=Path, default=Path("corrections/stage2_sample.csv"))
    parser.add_argument("--out", type=Path, default=Path("corrections/ledger_stage2.csv"))
    parser.add_argument("--limit", type=int, default=None,
                        help="Look up only the first N words (for smoke tests)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would be looked up, call nothing")
    parser.add_argument("--decided-date",
                        default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    with open(args.sample, "r", encoding="utf-8", newline="") as f:
        sample = list(csv.DictReader(f))
    if args.limit:
        sample = sample[:args.limit]

    logger.info("Sample: %d words", len(sample))
    logger.info("Order : %s", " -> ".join(LOOKUP_ORDER))
    logger.info("Cache : %s", "enabled" if cache_enabled() else "disabled")

    if args.dry_run:
        logger.info("Dry run: would make up to %d lookups across %d sources; "
                    "nothing called, nothing written",
                    len(sample) * len(LOOKUP_ORDER), len(LOOKUP_ORDER))
        return 0

    rows = asyncio.run(look_up_all(sample, args.decided_date))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to %s", len(rows), args.out)

    tally: dict[str, int] = {}
    for row in rows:
        tally[row["outcome"]] = tally.get(row["outcome"], 0) + 1
    for outcome in ("refuted", "corroborated", "unadjudicated", "error"):
        logger.info("  %-14s %4d", outcome, tally.get(outcome, 0))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
