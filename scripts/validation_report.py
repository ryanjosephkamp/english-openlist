"""
The night's verdict on the invalid-list lookups, as the last step of the nightly.

`validate_invalid_list.py` exits 0 on a night when no selected word could be
checked, so the rest of the run still publishes the lists. That left every such
night green: from November 2, 2026, the Free Dictionary API answered every
lookup with 403, and each run reported success with "validated": 0.

This reads the night's validation_summary.json after everything else has run
and says what happened, in the log, on the run's page, and in its summary:

- No selected word checked: the step fails, so the run ends red.
- Some words not checked: a warning, and the run stays green.
- Otherwise, or nothing to check: a plain line.

Usage: python scripts/validation_report.py [path/to/validation_summary.json]
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR, get_release_date

FAILED = "failed"
WARNING = "warning"
OK = "ok"


def statuses(summary: dict) -> str:
    """`403: 1,000`, or the empty string when no status was recorded."""
    by_status = summary.get("not_checked_by_status") or {}
    return ", ".join(f"{status}: {count:,}" for status, count in sorted(by_status.items()))


def verdict(summary: dict | None) -> tuple[str, str]:
    """The night's level (failed, warning, or ok) and the sentence that says why."""
    if summary is None:
        return FAILED, "The night wrote no validation summary, so there is no record of its lookups."
    if not summary.get("success", False):
        reason = summary.get("message") or "no reason recorded"
        return FAILED, f"The invalid-list validation did not run: {reason}."

    selected = summary.get("selected", 0)
    checked = summary.get("validated", 0)
    not_checked = summary.get("not_checked", 0)
    promoted = summary.get("promoted", 0)
    refused = statuses(summary)
    because = f" (HTTP {refused})" if refused else ""

    if not selected:
        return OK, summary.get("message") or "No word was selected for checking tonight."
    if not checked:
        return FAILED, (
            f"No word from the invalid list was checked tonight: all {selected:,} lookups "
            f"failed{because}. Nothing was promoted, and the lists were published as they were."
        )
    if not_checked:
        return WARNING, (
            f"{not_checked:,} of {selected:,} selected words could not be checked tonight{because}. "
            f"{checked:,} were checked and {promoted:,} promoted."
        )
    return OK, f"Checked {checked:,} of {selected:,} selected words; promoted {promoted:,}."


def load(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def report(level: str, message: str) -> int:
    """Print the verdict for the log and the run's page; 1 for a failed night."""
    if level == FAILED:
        print(f"::error title=No word was checked::{message}")
    elif level == WARNING:
        print(f"::warning title=Some words were not checked::{message}")
    else:
        print(message)

    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_file:
        heading = {FAILED: "Lookups failed", WARNING: "Some lookups failed", OK: "Lookups"}[level]
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(f"\n### {heading}\n\n{message}\n")

    return 1 if level == FAILED else 0


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else OUTPUT_DIR / get_release_date() / "validation_summary.json"
    return report(*verdict(load(path)))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
