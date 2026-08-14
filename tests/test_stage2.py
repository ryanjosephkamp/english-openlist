"""
Tests for the stage 2 sampling frame, sampler, outcome classifier and statistics.

Stage 2 produces one number that a decision about 20,052 words rests on. The
tests that matter here are the ones guarding the ways that number could be
confidently wrong:

  * a rate whose denominator quietly includes words nothing could rule on
  * an overall figure that ignores stratification and so overweights the
    stratum sampled at 8.9% against ones sampled at 1.6%
  * a variance that ignores the finite population correction and overstates the
    interval
  * an API error being read as "not a word", which is exactly how the daily
    pipeline already goes wrong

The interval maths is checked against values computed by hand rather than
against the implementation's own output, which would only prove it is
self-consistent.
"""

import csv
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.build_stage2_frame import build_frame, classify as classify_entry
from scripts.sample_stage2 import SAMPLE_SIZES, draw, rank_key
from scripts.run_stage2_lookups import classify
from scripts.stage2_report import POPULATION, stratified_estimate, summarise, wilson


# ------------------------------------------------------------------- the frame

def test_frame_takes_only_status_invalid_words():
    vd = {
        "abacavir": {"status": "invalid", "candidate_source": ["coca_frequency_valid"]},
        "a":        {"status": "valid"},
        "mpox":     {"status": "WordStatus.VALID"},
        "aalii":    {},
    }
    assert [r["word"] for r in build_frame(vd)] == ["abacavir"]


def test_frame_is_sorted_so_it_is_reproducible():
    vd = {w: {"status": "invalid"} for w in ("zeta", "alpha", "mu")}
    assert [r["word"] for r in build_frame(vd)] == ["alpha", "mu", "zeta"]


@pytest.mark.parametrize("sources,expected", [
    ([], "0"),
    (["a_unlikely", "b_unlikely"], "0"),
    (["a_valid"], "1"),
    (["a_valid", "b_valid"], "2"),
    (["a_valid", "b_valid", "c_valid"], "3"),
    (["a_valid"] * 4, "4+"),
    (["a_valid"] * 9, "4+"),
    (["a_valid", "b_unlikely"], "1"),
])
def test_stratum_counts_only_valid_suffixed_sources(sources, expected):
    assert classify_entry({"candidate_source": sources})["stratum"] == expected


def test_all_unlikely_separates_the_two_kinds_of_stratum_zero():
    """307 words have sources that all doubt them; 141 have no sources at all."""
    assert classify_entry({"candidate_source": ["a_unlikely"]})["all_unlikely"] is True
    assert classify_entry({"candidate_source": []})["all_unlikely"] is False
    assert classify_entry({})["all_unlikely"] is False


def test_pipeline_checks_passed_requires_every_present_check():
    entry = {
        "advanced_validation": {"passed": True},
        "statistical_validation": {"passed": False},
    }
    assert classify_entry(entry)["pipeline_checks_passed"] is False
    entry["statistical_validation"]["passed"] = True
    assert classify_entry(entry)["pipeline_checks_passed"] is True
    assert classify_entry({})["pipeline_checks_passed"] is False


# ----------------------------------------------------------------- the sampler

def make_frame(counts: dict[str, int]) -> list[dict]:
    return [
        {"word": f"{stratum}word{i}", "stratum": stratum, "n_valid_sources": "1",
         "all_unlikely": "False", "pipeline_checks_passed": "True", "gemini_source": "x"}
        for stratum, n in counts.items() for i in range(n)
    ]


def test_draw_takes_exactly_the_agreed_sizes():
    frame = make_frame({"0": 448, "1": 10056, "2": 4906, "3": 2254, "4+": 2388})
    sample = draw(frame, seed=1, sizes=SAMPLE_SIZES)

    got: dict[str, int] = {}
    for row in sample:
        got[row["stratum"]] = got.get(row["stratum"], 0) + 1
    assert got == SAMPLE_SIZES
    assert len(sample) == 400


def test_draw_is_deterministic_for_a_seed():
    frame = make_frame({"1": 500})
    a = draw(frame, seed=7, sizes={"1": 20})
    b = draw(frame, seed=7, sizes={"1": 20})
    assert [r["word"] for r in a] == [r["word"] for r in b]


def test_a_different_seed_draws_a_different_sample():
    frame = make_frame({"1": 500})
    a = {r["word"] for r in draw(frame, seed=7, sizes={"1": 20})}
    b = {r["word"] for r in draw(frame, seed=8, sizes={"1": 20})}
    assert a != b


def test_rank_key_is_salted_by_stratum_and_seed():
    assert rank_key(1, "0", "mpox") != rank_key(1, "1", "mpox")
    assert rank_key(1, "0", "mpox") != rank_key(2, "0", "mpox")
    assert rank_key(1, "0", "mpox") == rank_key(1, "0", "mpox")


def test_draw_refuses_to_oversample_a_stratum():
    with pytest.raises(ValueError, match="cannot draw"):
        draw(make_frame({"1": 5}), seed=1, sizes={"1": 10})


def test_draw_refuses_a_frame_missing_a_stratum():
    with pytest.raises(ValueError, match="no words in stratum"):
        draw(make_frame({"1": 50}), seed=1, sizes={"1": 10, "9": 1})


# ------------------------------------------------------------- the classifier

def test_a_dictionary_entry_refutes_the_llm():
    assert classify({"medical": "valid"}, "valid") == "refuted"


@pytest.mark.parametrize("status", ["abbreviation", "proper_noun"])
def test_an_abbreviation_or_proper_noun_corroborates_it(status):
    """This dataset excludes both, so the LLM calling them invalid was defensible."""
    assert classify({"medical": status}, status) == "corroborated"


def test_no_entry_anywhere_is_unadjudicated_not_agreement():
    statuses = {"medical": "not_found", "collegiate": "not_found", "free": "not_found"}
    assert classify(statuses, None) == "unadjudicated"


def test_every_source_failing_is_an_error_not_a_verdict():
    """The bug this avoids: validate_invalid_list.py reads ERROR as 'not a word'."""
    statuses = {"medical": "error", "collegiate": "error", "free": "error"}
    assert classify(statuses, None) == "error"


def test_one_real_no_alongside_an_error_is_still_unadjudicated():
    statuses = {"medical": "error", "collegiate": "not_found", "free": "not_found"}
    assert classify(statuses, None) == "unadjudicated"


def test_unconfigured_sources_do_not_count_as_answers():
    statuses = {"medical": "unconfigured", "collegiate": "error", "free": "error"}
    assert classify(statuses, None) == "error"


# ------------------------------------------------------------- the statistics

@pytest.mark.parametrize("successes,n,expected_lo,expected_hi", [
    (40, 50, 0.669629, 0.887562),
    (3, 40, 0.025836, 0.198642),
    (128, 160, 0.731315, 0.854617),
    (0, 20, 0.000000, 0.161125),
    (20, 20, 0.838875, 1.000000),
])
def test_wilson_matches_an_independent_implementation(successes, n, expected_lo, expected_hi):
    """
    Constants are statsmodels' `proportion_confint(..., method='wilson')`, checked
    once and pinned here — statsmodels is not a dependency of this project, and
    asserting against our own output would only prove self-consistency.
    """
    lo, hi = wilson(successes, n)
    assert lo == pytest.approx(expected_lo, abs=1e-6)
    assert hi == pytest.approx(expected_hi, abs=1e-6)


def test_wilson_stays_inside_zero_and_one_at_the_extremes():
    """Where the normal approximation reports impossible bounds."""
    lo, hi = wilson(0, 20)
    assert lo == 0.0 and 0 < hi < 1
    lo, hi = wilson(20, 20)
    assert hi == 1.0 and 0 < lo < 1


def test_wilson_of_an_empty_denominator_claims_nothing():
    assert wilson(0, 0) == (0.0, 1.0)


def test_overall_estimate_is_population_weighted_not_a_raw_average():
    """
    Stratum 0 is 40 of 448 sampled and stratum 1 is 160 of 10,056. A raw pooled
    rate would let the small, heavily-sampled stratum dominate a figure that is
    supposed to describe all 20,052 words.
    """
    per_stratum = {"0": (40, 40), "1": (0, 160)}   # 100% in stratum 0, 0% in stratum 1
    est, _, _ = stratified_estimate(per_stratum)

    pooled = 40 / 200                              # 20.0% if you ignore weights
    expected = POPULATION["0"] / (POPULATION["0"] + POPULATION["1"])   # ~4.3%

    assert est == pytest.approx(expected, abs=1e-6)
    assert est < pooled


def test_finite_population_correction_narrows_the_interval():
    """Stratum 0 samples 40 of 448; treating that as an infinite population overstates the spread."""
    est, lo, hi = stratified_estimate({"0": (20, 40)})
    width = hi - lo

    # Same proportion and sample size, drawn from a much larger stratum.
    est2, lo2, hi2 = stratified_estimate({"1": (20, 40)})
    assert est == pytest.approx(est2)
    assert width < (hi2 - lo2)


def test_strata_that_adjudicated_nothing_are_dropped_from_the_weights():
    est, _, _ = stratified_estimate({"0": (10, 20), "1": (0, 0)})
    assert est == pytest.approx(0.5)


def test_estimate_of_nothing_is_not_a_number():
    import math
    est, lo, hi = stratified_estimate({"0": (0, 0)})
    assert math.isnan(est) and math.isnan(lo) and math.isnan(hi)


def test_mw_only_demotes_free_dictionary_rulings():
    rows = [
        {"stratum": "1", "outcome": "refuted", "deciding_source": "free"},
        {"stratum": "1", "outcome": "refuted", "deciding_source": "collegiate"},
        {"stratum": "1", "outcome": "corroborated", "deciding_source": "medical"},
    ]
    measured = summarise(rows, mw_only=False)["1"]
    assert measured["refuted"] == 2 and measured["unadjudicated"] == 0

    strict = summarise(rows, mw_only=True)["1"]
    assert strict["refuted"] == 1
    assert strict["unadjudicated"] == 1


# ------------------------------------------------------- the shipped artefacts

def test_shipped_frame_matches_the_recorded_populations():
    path = ROOT / "corrections" / "stage2_frame.csv"
    if not path.exists():
        pytest.skip("frame not built")

    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["stratum"]] = counts.get(row["stratum"], 0) + 1

    assert len(rows) == 20_052
    assert counts == POPULATION
    assert len({r["word"] for r in rows}) == len(rows), "no duplicate words"


def test_shipped_sample_is_reproducible_from_the_shipped_frame():
    """
    The sample is committed before any lookup runs. This proves it is the one the
    recorded seed produces, so it could not have been chosen after seeing results.
    """
    frame_path = ROOT / "corrections" / "stage2_frame.csv"
    sample_path = ROOT / "corrections" / "stage2_sample.csv"
    if not (frame_path.exists() and sample_path.exists()):
        pytest.skip("frame or sample not built")

    with open(sample_path, encoding="utf-8", newline="") as f:
        shipped = list(csv.DictReader(f))
    with open(frame_path, encoding="utf-8", newline="") as f:
        frame = list(csv.DictReader(f))

    seed = int(shipped[0]["seed"])
    redrawn = draw(frame, seed=seed, sizes=SAMPLE_SIZES)

    assert len(shipped) == 400
    assert [r["word"] for r in shipped] == [r["word"] for r in redrawn]


def test_runner_dry_run_calls_nothing_and_writes_nothing(tmp_path):
    out = tmp_path / "ledger.csv"
    result = subprocess.run(
        [sys.executable, "scripts/run_stage2_lookups.py", "--dry-run", "--out", str(out)],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not out.exists()


# ------------------------------------------- partial runs must announce themselves

def test_a_source_never_asked_is_not_a_no():
    """
    `not_consulted` must not be readable as an answer. If it were, omitting a
    source would silently inflate the unadjudicated count and deflate the
    measured error rate.
    """
    from scripts.run_stage2_lookups import NOT_CONSULTED

    statuses = {"medical": "not_found", "free": "not_found"}
    assert classify(statuses, None) == "unadjudicated"

    # Every source that was actually asked errored; a skipped one changes nothing.
    statuses = {"medical": "error", "free": "error", "collegiate": NOT_CONSULTED}
    assert classify(statuses, None) == "error"


def test_report_warns_loudly_when_a_source_was_never_consulted(tmp_path):
    from scripts.stage2_report import main as report_main

    ledger = tmp_path / "ledger.csv"
    rows = [{
        "word": f"w{i}", "stage": "2", "stratum": "1", "gemini_verdict": "invalid",
        "outcome": "unadjudicated", "action": "none", "deciding_source": "",
        "deciding_status": "", "medical_status": "not_found",
        "collegiate_status": "not_consulted", "free_status": "not_found",
        "part_of_speech": "", "definition": "", "decided_date": "2026-08-14",
    } for i in range(5)]
    with open(ledger, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    out = tmp_path / "report.md"
    sys.argv = ["stage2_report.py", "--ledger", str(ledger), "--out", str(out)]
    assert report_main() == 0

    text = out.read_text()
    assert "partial run" in text.lower()
    assert "Collegiate" in text
    # The warning has to sit above the numbers, not in a footnote.
    assert text.index("partial run") < text.index("| Stratum |")


# ------------------------------------------------------------------- stage 3

def test_stage3_stem_recovery_handles_english_spelling_changes():
    from scripts.build_stage3_frame import candidate_stems
    assert "red" in candidate_stems("redder")        # doubled consonant
    assert "happy" in candidate_stems("happiest")    # y -> i
    assert "abatable" in candidate_stems("abatabler")
    assert "large" in candidate_stems("larger")      # silent e restored


def test_stage3_strata_split_on_whether_a_comparative_is_even_conceivable():
    from scripts.build_stage3_frame import classify
    assert classify({"a"}) == "wn-adj"
    assert classify({"s"}) == "wn-adj"        # satellite adjective
    assert classify({"n"}) == "wn-other"      # a comparative on a noun is bogus
    assert classify({"v"}) == "wn-other"
    assert classify(set()) == "not-in-wn"
    assert classify({"n", "a"}) == "wn-adj"   # gradable in at least one sense


def test_stage3_reads_inflections_out_of_mw_rather_than_guessing():
    from scripts.run_stage3_lookups import inflections_of
    raw = {"meta": {"id": "happy", "stems": ["happy", "happier", "happiest"]}}
    assert inflections_of(raw) == {"happy", "happier", "happiest"}
    assert inflections_of({"meta": {}}) == set()
    assert inflections_of(None) == set()


def test_stage3_sample_is_reproducible_from_the_shipped_frame():
    from scripts.sample_stage3 import SAMPLE_SIZES as S3_SIZES, draw as draw3

    frame_path = ROOT / "corrections" / "stage3_frame.csv"
    sample_path = ROOT / "corrections" / "stage3_sample.csv"
    if not (frame_path.exists() and sample_path.exists()):
        pytest.skip("stage 3 frame or sample not built")

    with open(sample_path, encoding="utf-8", newline="") as f:
        shipped = list(csv.DictReader(f))
    with open(frame_path, encoding="utf-8", newline="") as f:
        frame = list(csv.DictReader(f))

    redrawn = draw3(frame, seed=int(shipped[0]["seed"]), sizes=S3_SIZES)
    assert len(shipped) == 300
    assert [r["stem"] for r in shipped] == [r["stem"] for r in redrawn]


def test_shipped_stage3_frame_covers_every_er_est_form():
    path = ROOT / "corrections" / "stage3_frame.csv"
    if not path.exists():
        pytest.skip("stage 3 frame not built")
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 8_809
    assert sum(int(r["n_forms"]) for r in rows) == 16_478
    assert len({r["stem"] for r in rows}) == len(rows)
