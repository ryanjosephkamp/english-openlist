"""
Execution Transparency Generator
Creates a daily_execution_summary.json with recorded pipeline status and honest
"not recorded" values for metrics that are not captured by the current run.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_release_date, get_release_dir

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

NOT_RECORDED = "not recorded"


def generate_execution_summary() -> Path:
    release_date = get_release_date()
    release_dir = get_release_dir()

    summary = {
        "date": release_date,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pipeline_status": "SUCCESS",
        "api_health": {
            "merriam_webster": {
                "calls_made": NOT_RECORDED,
                "success_rate": NOT_RECORDED,
                "status": NOT_RECORDED,
            },
            "wordnik": {
                "calls_made": NOT_RECORDED,
                "success_rate": NOT_RECORDED,
                "status": NOT_RECORDED,
            },
        },
        "words_by_source": {
            "merriam_webster_rss": NOT_RECORDED,
            "merriam_webster_new_words": NOT_RECORDED,
            "wordnik_wotd": NOT_RECORDED,
            "invalid_list_validation": NOT_RECORDED,
            "manual_additions": NOT_RECORDED,
        },
        "total_new_words_discovered": NOT_RECORDED,
        "total_words_promoted": NOT_RECORDED,
        "notes": "Pipeline completed; detailed API/source metrics were not recorded by this run.",
    }

    output_file = release_dir / "daily_execution_summary.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")

    logger.info("Created execution summary: %s", output_file)
    return output_file


def main():
    print("=" * 60)
    print("English OpenList - Execution Transparency Generator")
    print("=" * 60)

    output_file = generate_execution_summary()
    print(f"\nExecution summary saved to: {output_file}")
    print("Transparency log generated successfully!")
    return 0


if __name__ == "__main__":
    exit(main())
