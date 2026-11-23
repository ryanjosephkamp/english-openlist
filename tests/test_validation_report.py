"""
A night that checked no word ends red, and the changelog gives tonight's
counts, not the running total.

From 2026-11-02 the Free Dictionary API answered every lookup with 403. Each
night wrote "validated": 0, "not_checked": 1000, the run stayed green, and the
changelog said "Validated 43,005 words from invalid list", which was the total
since the first night.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts import generate_changelog as changelog  # noqa: E402
from scripts import validation_report as report  # noqa: E402

REFUSED_NIGHT = {
    "success": True,
    "selected": 1000,
    "validated": 0,
    "promoted": 0,
    "still_invalid": 0,
    "not_checked": 1000,
    "not_checked_by_status": {"403": 1000},
    "total_validated": 43005,
    "total_promoted": 120,
}

GOOD_NIGHT = {
    "success": True,
    "selected": 1000,
    "validated": 1000,
    "promoted": 3,
    "not_checked": 0,
    "not_checked_by_status": {},
    "total_validated": 43005,
}

PARTIAL_NIGHT = {**GOOD_NIGHT, "validated": 994, "not_checked": 6, "not_checked_by_status": {"429": 6}}


# ------------------------------------------------------------- the verdict

def test_a_night_that_checked_no_word_fails_and_says_why():
    level, message = report.verdict(REFUSED_NIGHT)
    assert level == report.FAILED
    assert "all 1,000 lookups failed (HTTP 403: 1,000)" in message


def test_a_night_with_some_words_unchecked_warns():
    level, message = report.verdict(PARTIAL_NIGHT)
    assert level == report.WARNING
    assert "6 of 1,000" in message and "429: 6" in message


def test_a_night_that_checked_its_words_passes():
    assert report.verdict(GOOD_NIGHT) == (report.OK, "Checked 1,000 of 1,000 selected words; promoted 3.")


def test_nothing_to_check_is_not_a_failure():
    level, _ = report.verdict({"success": True, "promoted": 0, "validated": 0, "message": "No words"})
    assert level == report.OK


def test_a_missing_or_unsuccessful_summary_fails():
    assert report.verdict(None)[0] == report.FAILED
    assert report.verdict({"success": False, "message": "source files are not writable"})[0] == report.FAILED


def test_the_step_flags_a_refused_night_and_still_exits_0(tmp_path, monkeypatch, capsys):
    path = tmp_path / "validation_summary.json"
    path.write_text(json.dumps(REFUSED_NIGHT))
    step_summary = tmp_path / "step_summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(step_summary))

    assert report.main(["validation_report.py", str(path)]) == 0
    assert capsys.readouterr().out.startswith("::error title=No word was checked::")
    assert "### Lookups failed" in step_summary.read_text()

    path.write_text(json.dumps(PARTIAL_NIGHT))
    assert report.main(["validation_report.py", str(path)]) == 0
    assert capsys.readouterr().out.startswith("::warning ")

    path.write_text(json.dumps(GOOD_NIGHT))
    assert report.main(["validation_report.py", str(path)]) == 0


# ------------------------------------------------------------- the changelog

def test_the_changelog_line_gives_tonights_counts():
    assert changelog.validation_line(REFUSED_NIGHT) == (
        "No word from the invalid list could be checked today: all 1,000 lookups failed (HTTP 403: 1,000)."
    )
    assert changelog.validation_line(GOOD_NIGHT) == (
        "Checked 1,000 of 1,000 words selected from the invalid list today."
    )
    assert changelog.validation_line(PARTIAL_NIGHT).endswith("6 could not be checked (HTTP 429: 6).")
    assert changelog.validation_line(None) == "No invalid list validation ran today."


def test_a_refused_night_never_shows_the_running_total_as_its_work(tmp_path, monkeypatch):
    monkeypatch.setattr(changelog, "OUTPUT_DIR", tmp_path)
    release_dir = tmp_path / "2026-11-21"
    release_dir.mkdir()
    (release_dir / "validation_summary.json").write_text(json.dumps(REFUSED_NIGHT))
    monkeypatch.setattr(changelog, "load_validation_progress", lambda _root: {"validated_count": 43005, "promoted_count": 120})

    changelog.generate_changelog("2026-11-21")

    text = (release_dir / "CHANGELOG.md").read_text()
    assert "Validated 43,005" not in text
    assert "_No word from the invalid list could be checked today: all 1,000 lookups failed (HTTP 403: 1,000)._" in text
    assert "- Words checked from invalid list today: 0" in text
    assert "- Cumulative words checked from invalid list: 43,005" in text
