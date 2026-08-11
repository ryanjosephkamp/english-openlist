# Change Log: Brrrdle Length-Specific Artifact Generation

## What changed

- Saved the approved implementation plan at `change-logs/change-log-2026-05-24/implementation-plan.md`.
- Extended `scripts/generate_brrrdle_artifacts.py` to generate primary Brrrdle JSON files for every supported length from 2 through 35:
  - `words_length_2.json`
  - `words_length_3.json`
  - ...
  - `words_length_35.json`
- Changed each primary length file to contain a JSON array of objects with a required `word` field.
- Added optional `definition` fields to primary Brrrdle entries when a non-empty top-level definition is available from valid dictionary metadata.
- Kept transitional legacy length-5 files for compatibility:
  - `brrrdle_words.txt`
  - `brrrdle_words.json`
- Updated `manifest.json` generation to include:
  - `schema_version`
  - supported word length range
  - all primary length-specific files
  - per-length counts
  - total Brrrdle word count
  - transitional legacy compatibility file names
- Updated the daily workflow to verify all 34 expected `words_length_{N}.json` files exist after generation and before upload.
- Updated tests for multi-length grouping, primary file generation, optional definitions, manifest metadata, generated README content, and legacy compatibility files.
- Updated `README.md` and `templates/dataset_card.md` to document the new Brrrdle artifact format and the legacy-file transition.

## Key decisions

- Full Brrrdle generation now defaults to the inclusive length range 2 through 35.
- Words outside 2 through 35 continue to be ignored for Brrrdle artifacts.
- Definitions are sourced only from the top-level `definition` field in valid dictionary metadata.
- Missing, blank, or non-string definitions are omitted from individual Brrrdle entries.
- Hugging Face upload routing remains unchanged; the existing folder upload still publishes the generated Brrrdle directory to both `latest/brrrdle/` and `data/brrrdle/`.
- Legacy length-5 files remain for one transition period and should be removed in the next major Brrrdle artifact update.

## Validation performed

- Installed existing repository requirements from `requirements.txt` when the sandbox did not have `pytest` available.
- Ran the full test suite with `pytest tests/ -v`: 27 tests passed.
- Ran a local generator invocation into a temporary `/tmp` directory.
- Verified exactly 34 primary `words_length_{N}.json` files were generated.
- Verified `manifest.json` includes `schema_version: "2.0"`.
- Verified `manifest.json` lists every primary file from `words_length_2.json` through `words_length_35.json`.
- Verified primary entries include `definition` only when available.
- Verified transitional length-5 compatibility files are present.
- Verified no generated `latest/`, `data/brrrdle/`, or `output/**/brrrdle/` artifacts were staged for commit.
