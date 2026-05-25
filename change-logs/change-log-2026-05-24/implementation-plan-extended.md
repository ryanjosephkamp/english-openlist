# Extended Implementation Plan

## Current state reviewed

- The latest reviewed `Daily Dictionary Update` run on 2026-05-24 completed successfully.
- The run generated Brrrdle artifacts at `output/2026-05-24/brrrdle/`.
- The generated workflow artifact contained the current four legacy Brrrdle files:
  - `brrrdle_words.txt`
  - `brrrdle_words.json`
  - `manifest.json`
  - `README.md`
- The current Brrrdle JSON shape is a metadata wrapper with a `words` array of strings, not one file per length and not an array of `{ "word": ..., "definition": ... }` objects.
- The latest generated manifest showed `word_length: 5` and `word_count: 9776`.
- Hugging Face upload logs confirmed the Brrrdle folder was uploaded to both remote paths:
  - `latest/brrrdle/`
  - `data/brrrdle/`
- Direct inspection of the Hugging Face web and API URLs from this sandbox failed due DNS/fetch errors, so the remote release listing could not be independently verified here.

## Why generation is currently limited to length 5

- `scripts/generate_brrrdle_artifacts.py` defines `DEFAULT_WORD_LENGTH = 5`.
- `normalize_brrrdle_words()` filters to a single `word_length`, defaulting to 5.
- `write_brrrdle_artifacts()` writes one shared `brrrdle_words.txt`, one shared `brrrdle_words.json`, one `manifest.json`, and one `README.md` for that single configured length.
- `.github/workflows/daily_update.yml` calls the generator without `--word-length`, so the default length 5 is always used.
- `scripts/push_to_huggingface.py` already uploads the whole generated Brrrdle directory to `latest/brrrdle/` and `data/brrrdle/`, so upload routing does not need major redesign.

## Approved decisions

- Generate the new primary Brrrdle artifacts as length-specific JSON files for lengths 2 through 35.
- Continue ignoring words longer than 35 letters for the Brrrdle use case.
- Omit the `definition` key entirely when no definition is available.
- Use only the top-level `definition` field from the dictionary metadata.
- Keep Hugging Face upload logic unchanged.
- Make full 2-35 generation the default behavior for daily automation.
- Keep legacy length-5 files for one transition period, then remove them in a later major update.
- Update the manifest to focus on the new per-length files.
- Add a lightweight verification step before upload to ensure all 34 expected length-specific JSON files exist.

## Goal

Extend the existing transient Brrrdle artifact generation so the daily automation creates 34 primary JSON files:

- `words_length_2.json`
- `words_length_3.json`
- ...
- `words_length_35.json`

Each primary file should be a JSON array of objects. Each object should include:

- `word`
- `definition`, only when available from the valid dictionary metadata

The generated files should remain transient build outputs and should continue to be uploaded to Hugging Face under:

- `latest/brrrdle/`
- `data/brrrdle/`

## Minimal-change implementation approach

1. Keep the existing Brrrdle artifact directory convention.
   - Continue generating under `output/{date}/brrrdle/`.
   - Continue relying on `.gitignore` rules that keep generated Brrrdle artifacts out of committed repository data folders.
   - Continue using `upload_brrrdle_artifacts()` to upload the whole Brrrdle directory to both Hugging Face destinations.

2. Extend `scripts/generate_brrrdle_artifacts.py`.
   - Add constants for the inclusive supported length range: 2 through 35.
   - Load the valid word list as the source of eligible words.
   - Also load `VALID_DICT_FILE` when present, so definitions can be included when available.
   - Preserve the existing lowercase ASCII alphabetic filtering rules.
   - Group normalized words by length for all lengths 2 through 35.
   - Write one JSON file per length using the filename pattern `words_length_{N}.json`.
   - For each word entry, write `{ "word": word }` and add `definition` only when the corresponding dictionary metadata has a non-empty top-level `definition`.

3. Phase out legacy artifacts safely.
   - Keep `brrrdle_words.txt` and `brrrdle_words.json` for one transition period as length-5 compatibility artifacts.
   - Keep `manifest.json`, but update it to focus on the new `words_length_{N}.json` files and per-length counts.
   - Keep `README.md`, but update it to document the new primary per-length files and note that the old length-5 files are transitional compatibility outputs.
   - Do not add new repository data folders for `latest/brrrdle/` or `data/brrrdle/`.

4. Keep the workflow simple.
   - Prefer changing the generator default so the existing workflow generation step continues to produce all required files:
     `python scripts/generate_brrrdle_artifacts.py --output-dir output/${{ steps.date.outputs.date }}/brrrdle --date ${{ steps.date.outputs.date }}`
   - Avoid adding 34 workflow commands; the script should own multi-length generation.
   - Add a lightweight verification command after generation and before upload to confirm all 34 files exist.

5. Keep upload logic unchanged.
   - Continue uploading the entire generated `brrrdle/` folder to `latest/brrrdle/`.
   - Continue uploading the entire generated `brrrdle/` folder to `data/brrrdle/`.
   - No Hugging Face path restructuring is needed for this extension.

6. Update tests.
   - Replace or extend the five-letter-only normalization test with coverage for multiple lengths.
   - Add tests confirming `words_length_2.json` through `words_length_35.json` are generated.
   - Add tests confirming each length file is a JSON array of objects with `word`.
   - Add tests confirming `definition` is included when available and omitted when unavailable.
   - Add tests confirming the manifest lists all 34 primary files and their per-length counts.
   - Add tests confirming the transitional length-5 legacy artifacts are still generated for now.
   - Keep existing Hugging Face upload tests focused on folder upload paths, since remote path behavior should remain unchanged.

7. Validate.
   - Run the existing test suite with `pytest tests/ -v`.
   - Run a local generator invocation into a temporary directory and verify exactly the expected 34 primary length JSON files are created.
   - Verify the manifest lists every `words_length_{N}.json` file from 2 through 35.
   - Verify legacy length-5 compatibility files are present for the transition period.
   - Confirm no generated `latest/`, `data/brrrdle/`, or `output/**/brrrdle/` artifacts are staged for commit.

## Clarification questions

None.

## Additional recommendations

- Document in `README.md` or the Hugging Face dataset card that `words_length_{N}.json` files are the new primary Brrrdle artifacts.
- Add a follow-up task to remove the legacy length-5 compatibility files after the transition period.
- Consider including a `schema_version` field in `manifest.json` so downstream consumers can distinguish the new multi-length artifact format from the legacy single-length format.

## Halt point

No code changes should be made until this revised plan is approved.
