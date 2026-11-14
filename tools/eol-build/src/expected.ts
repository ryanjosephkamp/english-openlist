/**
 * What the dataset looked like when this build was last checked against it.
 *
 * These are tripwires, not configuration. The list grows every night by
 * design, a word or 2 promoted from the invalid list, so exact equality would
 * fail the build daily and teach everyone to ignore it. Instead each figure
 * carries the tolerance that tells "the nightly run ran" from "the dataset
 * changed shape".
 *
 * A trip here means the assumptions this site is built on have moved. Read the
 * failure before widening the bound.
 */
export const EXPECTED = {
  /**
   * 344,830 words on November 13, 2026. The list grows by about 1 a night, so
   * a shrink is the alarm: a correction that removes words is recorded in a
   * ledger in `corrections/`, and the floor moves with it.
   */
  words: { min: 344_000, max: 400_000 },

  /**
   * The synthetic engine's share of the list: 31,243 words, 9.06%, on
   * November 13, 2026. The engine adds no words, so the share falls as the
   * list grows. A rise would mean generated words are being added, and the
   * upper bound is tight for that reason.
   */
  engineShare: { min: 0.0, max: 0.092 },

  /**
   * The share that at least 1 open source lists: 268,762 words, 77.94%, on
   * November 13, 2026. A word the nightly run adds is not checked against the
   * open sources until the next pass, so the share drifts down slowly between
   * passes. A large move means `attested_by` changed meaning or went missing.
   */
  attestedShare: { min: 0.74, max: 0.82 },

  /**
   * Words whose record has no `attested_by` yet: 0 on November 13, 2026. The
   * nightly run adds a word or 2 a night without it; thousands would mean the
   * field was dropped, and the site would call those words not checked.
   */
  notChecked: { min: 0, max: 5_000 },

  /**
   * Records that carry a date but no published `source`: 0. The site shows a
   * word's date only when its record names a published intake, and the build
   * drops any other date; this makes such a record fail the build too.
   */
  datedUnlabeled: { min: 0, max: 0 },

  /**
   * Records with a field outside `word`, `length`, `attested_by`, `source`, and
   * `added_date`: 0. The site reads none of the others, and a new field is a
   * change to the published shape that someone should look at first.
   */
  unexpectedFields: { min: 0, max: 0 },

  /**
   * Words in both the valid and the invalid list: 0, the one correct answer.
   * Above 0 means the promotion path in `scripts/validate_invalid_list.py` has
   * stopped removing a word from the invalid list when it promotes it.
   * Widening the bound is the wrong fix.
   */
  alsoInvalid: { min: 0, max: 0 },

  /**
   * Words with anything outside `a-z`: 0. The form rule `^[a-z]+$` is enforced
   * in `scripts/word_validator.py`, so above 0 means an ingest path has stopped
   * validating. Widening the bound is the wrong fix.
   */
  nonAlpha: { min: 0, max: 0 },
} as const;

export type Bound = { readonly min: number; readonly max: number };

const tripped: string[] = [];

export function check(label: string, value: number, bound: Bound, detail = ''): void {
  if (value >= bound.min && value <= bound.max) return;
  tripped.push(
    `${label}: ${value.toLocaleString()} is outside [${bound.min.toLocaleString()}, ` +
      `${bound.max.toLocaleString()}]${detail ? ` — ${detail}` : ''}`,
  );
}

/**
 * Fail the build if any tripwire fired, reporting all of them at once.
 *
 * All of them, rather than the first: when the dataset shifts, several bounds
 * usually move together, and fixing them one build at a time wastes a download
 * per attempt.
 */
export function assertExpectations(): void {
  if (tripped.length === 0) return;
  throw new Error(
    `The dataset no longer matches what this build was verified against:\n` +
      tripped.map((line) => `  - ${line}`).join('\n') +
      `\n\nRead tools/eol-build/src/expected.ts before widening a bound.`,
  );
}
