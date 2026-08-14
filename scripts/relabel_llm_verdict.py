"""
Relabel the `status` field to say what it actually is.

`status` looked like the dataset's own verdict on a word. It was not. For
137,705 entries it is the opinion of one LLM — Google Gemini 3 Flash Preview,
December 2025 — recorded and never acted on, and it was demonstrably wrong: of
the words a real dictionary could rule on in the stage 2 sample, it got 13 of 18
wrong, including `clorazepate` and `antinociceptive`.

Nobody reading `"status": "invalid"` would guess any of that. So the field is
renamed to carry its own warning:

    status -> unverified_llm_verdict     137,705 entries
    status -> dictionary_verdict            201 entries

The split matters. Those 201 are not LLM output at all: they came through the
promotion path and their verdict is Merriam-Webster's or Free Dictionary's,
recorded alongside `source`. Renaming them "unverified LLM" would be a fresh
lie in the opposite direction, so they get their own accurate name. They are
identifiable without guessing: an entry whose verdict came from the LLM always
carries a `manual_validation` block, and these carry none.

No word moves. No word is added or removed. Only a key is renamed, and the
values are untouched.

Usage:
    python scripts/relabel_llm_verdict.py --data-dir .cache/hf --dry-run
    python scripts/relabel_llm_verdict.py --data-dir .cache/hf
"""

import argparse
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

OLD_FIELD = "status"
LLM_FIELD = "unverified_llm_verdict"
API_FIELD = "dictionary_verdict"


def relabel(valid_dict: dict) -> dict[str, int]:
    """
    Rename `status` where it sits. Returns a tally of what went where.

    An entry is treated as LLM-sourced when it carries a `manual_validation`
    block, which is what recorded the verdict in the first place. Everything
    else with a `status` came from a dictionary API via the promotion path.

    The rebuild preserves key order deliberately. Popping the key and assigning
    the new one would move it to the end of the entry, which is invisible in the
    parsed data and catastrophic in the file: every following line shifts, and a
    one-key rename turns into a 6.9-million-line diff on a 291 MB published
    artifact. Renaming in place keeps the diff to the 137,906 lines that
    genuinely changed.
    """
    counts = {LLM_FIELD: 0, API_FIELD: 0, "untouched": 0, "already_renamed": 0}

    for word, entry in valid_dict.items():
        if LLM_FIELD in entry or API_FIELD in entry:
            counts["already_renamed"] += 1
            continue
        if OLD_FIELD not in entry:
            counts["untouched"] += 1
            continue

        field = LLM_FIELD if entry.get("manual_validation") else API_FIELD
        valid_dict[word] = {
            (field if key == OLD_FIELD else key): value
            for key, value in entry.items()
        }
        counts[field] += 1

    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Relabel the status field")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="Report what would change, write nothing")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")

    path = args.data_dir / "merged_valid_dict.json"
    with open(path, "r", encoding="utf-8") as f:
        valid_dict = json.load(f)
    logger.info("Loaded %d entries", len(valid_dict))

    before = len(valid_dict)
    counts = relabel(valid_dict)

    logger.info("  %-24s %7d", LLM_FIELD, counts[LLM_FIELD])
    logger.info("  %-24s %7d", API_FIELD, counts[API_FIELD])
    logger.info("  %-24s %7d", "no verdict field", counts["untouched"])
    logger.info("  %-24s %7d", "already renamed", counts["already_renamed"])

    # The only thing this script is allowed to do is rename a key.
    assert len(valid_dict) == before, "entry count changed"
    assert not any(OLD_FIELD in e for e in valid_dict.values()), \
        "some entries still carry the old field"

    if args.dry_run:
        logger.info("Dry run: nothing written")
        return 0

    with open(path, "w", encoding="utf-8") as f:
        json.dump(valid_dict, f, indent=2, ensure_ascii=False)
    logger.info("Wrote %s", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
