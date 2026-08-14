"""
Stage 3 Lookup Runner

Asks Merriam-Webster whether a comparative is a real inflection of its stem.

**This script moves nothing.** It reads the sample, calls dictionaries, and
writes a ledger.

The question is not "is `abacteremicer` a headword" — it never will be, and
asking would only produce "not found" 8,809 times. It is: does Merriam-Webster
list `abacteremicer` among the inflections of `abacteremic`? MW records those in
`meta.stems`, which is already how `_entry_matches_word` resolves plurals, so
the answer is read straight out of the response rather than inferred.

Outcomes per stem:

    inflection-listed   MW has the stem and lists the comparative -> the
                        synthetic form is a real inflection
    inflection-absent   MW has the stem and does not list it -> the form is not
                        a recognised inflection of a word MW does know
    mw-absent           MW has no entry for the stem -> nothing follows, exactly
                        as in stage 2
    error               the lookup failed; never counted as an answer

`mw-absent` is the number to read first. Stage 2 found MW had no entry for 95.8%
of a different set, and if that repeats here the method cannot answer this
question either — in which case the honest move is to say so and stop rather
than publish another interval nobody can act on.

Usage:
    python scripts/run_stage3_lookups.py --limit 60      # coverage probe
    EOL_DICT_CACHE=1 python scripts/run_stage3_lookups.py
"""

import argparse
import asyncio
import csv
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.dictionary_api import DictionaryAPIClient, WordStatus, cache_enabled

logger = logging.getLogger(__name__)

#: Collegiate first here, unlike stage 2. These stems are ordinary-shaped English
#: adjectives more often than they are medical terms, and stage 2 established
#: there is no quota pressure to route around.
LOOKUP_ORDER = ("collegiate", "medical", "free")

LEDGER_FIELDS = [
    "stem", "stage", "stratum", "outcome", "action",
    "forms", "n_forms", "forms_listed", "forms_missing",
    "deciding_source", "stem_status", "mw_stems", "part_of_speech", "decided_date",
]


def inflections_of(raw: dict | None) -> set[str]:
    """The inflected forms MW records for a headword."""
    if not isinstance(raw, dict):
        return set()
    meta = raw.get("meta") or {}
    return {str(s).lower() for s in (meta.get("stems") or [])}


async def look_up(sample: list[dict], decided: str) -> list[dict]:
    client = DictionaryAPIClient()
    rows = []

    for i, entry in enumerate(sample, 1):
        stem = entry["stem"]
        forms = entry["forms"].split()

        found = await client.lookup_all(stem, order=LOOKUP_ORDER)
        result = found["result"]
        statuses = found["statuses"]

        listed: list[str] = []
        missing: list[str] = []
        mw_stems: set[str] = set()

        if result is not None and result.status == WordStatus.VALID:
            mw_stems = inflections_of(result.raw_response)
            for form in forms:
                (listed if form.lower() in mw_stems else missing).append(form)
            # A source with no stems array cannot answer the inflection question,
            # only the does-the-stem-exist one. Free Dictionary is such a source.
            outcome = "inflection-listed" if listed else (
                "inflection-absent" if mw_stems else "no-stems-array")
        elif result is not None:
            # ABBREVIATION or PROPER_NOUN: MW has it, but not as a gradable word.
            outcome = "inflection-absent"
            missing = forms
        elif any(s == WordStatus.NOT_FOUND.value for s in statuses.values()):
            outcome = "mw-absent"
        else:
            outcome = "error"

        rows.append({
            "stem": stem,
            "stage": "3",
            "stratum": entry["stratum"],
            "outcome": outcome,
            "action": "none",
            "forms": entry["forms"],
            "n_forms": entry["n_forms"],
            "forms_listed": " ".join(listed),
            "forms_missing": " ".join(missing),
            "deciding_source": found["deciding_source"] or "",
            "stem_status": result.status.value if result else "",
            "mw_stems": " ".join(sorted(mw_stems))[:200],
            "part_of_speech": (result.part_of_speech if result else "") or "",
            "decided_date": decided,
        })

        if i % 25 == 0 or i == len(sample):
            logger.info("  %d/%d looked up", i, len(sample))

    logger.info("Cache: collegiate %d/%d, medical %d/%d, free %d/%d",
                client.mw.cache.hits, client.mw.cache.misses,
                client.mw_medical.cache.hits if client.mw_medical else 0,
                client.mw_medical.cache.misses if client.mw_medical else 0,
                client.free_dict.cache.hits, client.free_dict.cache.misses)
    return rows


def report(rows: list[dict]) -> None:
    """The coverage gate, printed before anything else."""
    tally = Counter(r["outcome"] for r in rows)
    absent = tally["mw-absent"]
    total = len(rows)

    logger.info("")
    logger.info("  %-20s %4d", "inflection-listed", tally["inflection-listed"])
    logger.info("  %-20s %4d", "inflection-absent", tally["inflection-absent"])
    logger.info("  %-20s %4d", "no-stems-array", tally["no-stems-array"])
    logger.info("  %-20s %4d", "mw-absent", absent)
    logger.info("  %-20s %4d", "error", tally["error"])
    logger.info("")
    logger.info("  COVERAGE: Merriam-Webster has %d of %d stems (%.1f%%)",
                total - absent - tally["error"], total,
                (total - absent - tally["error"]) / total * 100 if total else 0)

    if total and absent / total > 0.8:
        logger.warning("")
        logger.warning("  STOP: MW has no entry for %.1f%% of these stems.",
                       absent / total * 100)
        logger.warning("  The same wall stage 2 hit. A rate computed from what is "
                       "left will not be worth acting on.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the stage 3 lookups")
    parser.add_argument("--sample", type=Path, default=Path("corrections/stage3_sample.csv"))
    parser.add_argument("--out", type=Path, default=Path("corrections/ledger_stage3.csv"))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--decided-date",
                        default=datetime.now(timezone.utc).date().isoformat())
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    with open(args.sample, "r", encoding="utf-8", newline="") as f:
        sample = list(csv.DictReader(f))
    if args.limit:
        sample = sample[:args.limit]

    logger.info("Sample: %d stems covering %d forms",
                len(sample), sum(int(r["n_forms"]) for r in sample))
    logger.info("Order : %s", " -> ".join(LOOKUP_ORDER))
    logger.info("Cache : %s", "enabled" if cache_enabled() else "disabled")

    if args.dry_run:
        logger.info("Dry run: nothing called, nothing written")
        return 0

    rows = asyncio.run(look_up(sample, args.decided_date))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows to %s", len(rows), args.out)

    report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
