# Change Log: Brrrdle Answers Curation

## What changed

- Created `BRRRDLE-ANSWERS-CURATION-IMPLEMENTATION-PLAN.md` at the repository root.
- Documented a phased plan for implementing the answers curation algorithm from `BRRRDLE-ANSWERS-CURATION-SPEC.md`.
- Included verification commands after each major implementation phase.
- Recorded that the planned implementation must preserve complete `validGuesses`, add curated `answers`, and include the required curation metadata block.
- Implemented deterministic Brrrdle answers curation in `scripts/generate_brrrdle_artifacts.py`.
- Added the spec-defined target sample size calculation.
- Added curation metadata with `method`, `seed`, `target_sample_size`, `curation_date`, and `note`.
- Added stratified starting-letter answer selection with quality-score ranking.
- Preserved complete per-length `validGuesses` while adding curated `answers`.
- Aligned primary per-length `answers` and `validGuesses` payloads to the spec's plain word-string list shape.
- Updated Brrrdle artifact tests for target sizing, metadata, small-list behavior, deterministic large-list curation, primary artifact shape, and legacy compatibility files.
- Updated daily workflow verification to validate curation metadata, string-only `answers` and `validGuesses`, and subset membership.
- Updated Brrrdle documentation in `README.md`, `templates/dataset_card.md`, and the generated artifact README text.

## Verification performed

- Baseline before implementation: `pytest tests/ -v` — 27 passed.
- After generator/test update: `python -m pytest tests/test_generate_brrrdle_artifacts.py -v` — 5 passed.
- Final full test suite: `pytest tests/ -v` — 30 passed.
- Manual artifact generation and shape verification:
  - The default generator command could not run in this sandbox because `initial_deliverables/merged_valid_words.txt` is not present in the checkout.
  - Re-ran generation with the current checked-in output word list: `python scripts/generate_brrrdle_artifacts.py --input output/2026-05-27/merged_valid_words.txt --dictionary output/2026-05-27/merged_valid_dict.json --output-dir /tmp/brrrdle-curation-check --date 2026-05-27`.
  - The dictionary metadata path was absent in the sandbox, so generation continued with the existing warning behavior and no definitions.
  - Verified all `words_length_2.json` through `words_length_35.json` files exist.
  - Verified each payload has `metadata.curation.method == "stratified_quality_score_v1"`.
  - Verified each payload has seed `42 + length`.
  - Verified each payload has list-valued `answers` and `validGuesses`.
  - Verified no `answers` list is longer than its `validGuesses` list.
  - Verified every answer word is present in `validGuesses`.
- Documentation/search verification: `grep -R "validGuesses\\|stratified_quality_score_v1\\|answers" README.md templates scripts/generate_brrrdle_artifacts.py .github/workflows/daily_update.yml` found the expected references.
- Diff whitespace check: `git diff --check` — passed.
