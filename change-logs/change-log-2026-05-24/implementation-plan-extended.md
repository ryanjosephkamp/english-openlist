# Extended Implementation Plan

## Current state reviewed

- The latest reviewed `Daily Dictionary Update` run on 2026-05-24 completed successfully.
- The run generated Brrrdle artifacts at `output/2026-05-24/brrrdle/`.
- The generated workflow artifact contained exactly the current four Brrrdle files:
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

## Goal

Extend the existing transient Brrrdle artifact generation so the daily automation creates 34 JSON files:

- `words_length_2.json`
- `words_length_3.json`
- ...
- `words_length_35.json`

Each file should be a JSON array of objects. Each object should include:

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
   - For each word entry, write `{ "word": word }` and add `definition` only when the corresponding dictionary metadata has a non-empty definition.

3. Preserve compatibility where useful.
   - Keep the CLI entry point and existing arguments.
   - Keep `--word-length` available only if it is still useful for targeted/manual generation, but make the daily/default behavior generate the full 2-35 range.
   - Update metadata/manifest behavior to describe the multi-file output instead of one five-letter file.
   - Decide whether to keep, deprecate, or remove the old `brrrdle_words.txt` and `brrrdle_words.json` artifacts. Minimal risk option: keep them for length 5 during one transition unless the downstream consumer requires only the new files.

4. Update the daily workflow only if necessary.
   - Prefer changing the generator default so the existing workflow step continues to work:
     `python scripts/generate_brrrdle_artifacts.py --output-dir output/${{ steps.date.outputs.date }}/brrrdle --date ${{ steps.date.outputs.date }}`
   - Avoid adding 34 workflow commands; the script should own multi-length generation.

5. Update tests.
   - Replace or extend the five-letter-only normalization test with coverage for multiple lengths.
   - Add tests confirming `words_length_2.json` through `words_length_35.json` are generated.
   - Add tests confirming each length file is a JSON array of objects with `word`.
   - Add tests confirming `definition` is included when available and omitted when unavailable.
   - Keep existing Hugging Face upload tests focused on folder upload paths, since remote path behavior should remain unchanged.

6. Validate.
   - Run the existing test suite with `pytest tests/ -v`.
   - Run a local generator invocation into a temporary directory and verify exactly the expected length JSON files are created.
   - Confirm no generated `latest/`, `data/brrrdle/`, or `output/**/brrrdle/` artifacts are staged for commit.

## Clarification questions

1. Should the legacy `brrrdle_words.txt`, `brrrdle_words.json`, `manifest.json`, and generated Brrrdle `README.md` remain alongside the new `words_length_{N}.json` files, or should the Brrrdle folder contain only the 34 length-specific JSON files?
2. Should words longer than 35 continue to be ignored even though the current release word-length distribution includes lengths above 35?
3. Should a word object omit `definition` when unavailable, or include `"definition": null`?
4. If dictionary metadata contains multiple definition-like fields in the future, should only the top-level `definition` field be used?

## Recommendations

- Keep upload logic unchanged because it already uploads the entire generated Brrrdle folder to both required Hugging Face remote paths.
- Make the generator default produce the full 2-35 range so the daily workflow remains simple.
- Preserve old length-5 artifacts temporarily only if an existing Brrrdle consumer depends on them.
- Add a manifest listing every generated `words_length_{N}.json` file and per-length counts to make remote verification easier.
- Add a lightweight workflow or script assertion that verifies all 34 expected JSON files exist before the Hugging Face upload step.

## Halt point

No code changes should be made until this revised plan and the clarification questions above are approved.
