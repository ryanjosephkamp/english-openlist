/**
 * What the dataset looked like when this build was last verified against it.
 *
 * These are tripwires, not configuration. English OpenList grows every night by
 * design — a word or two promoted from the invalid list — so exact equality
 * would fail the build daily and teach everyone to ignore it. Instead each
 * figure carries the tolerance that distinguishes "the pipeline ran" from "the
 * dataset changed shape".
 *
 * A trip here means the assumptions this site is built on have moved. Read the
 * failure before widening the bound.
 */
export const EXPECTED = {
  /**
   * 345,297 on 2026-08-14. Grows by roughly one a day; shrinking is the alarm.
   *
   * It has shrunk twice, both deliberately, both on the same day and the same
   * method — ask Merriam-Webster which inflections it records for a stem, and
   * demote the synthetic forms it does not list:
   *
   *   378,891 -> 362,415  16,476 comparatives and superlatives
   *   362,415 -> 345,297  17,118 gerund plurals, verb forms, agent plurals
   *
   * A third, on 2026-08-16, for a different reason — the form rules changed
   * (D-025) and the list was corrected to match them:
   *
   *   345,301 -> 345,103  190 entries that never satisfied the form rule
   *                       (188 hyphenated, 2 accented), plus 8 single letters
   *                       moved to candidate status. `a` and `i` stay.
   *
   * That is the whole of it, and the floor moves from 345,200 to 345,000 to
   * match. Those are the only sanctioned shrinks. Another one is a bug until
   * someone writes it down here.
   *
   * The 28,605 synthetic plurals were deliberately NOT demoted: Merriam-Webster
   * could rule on only 9.2% of their stems and accepted four of the eleven it
   * could, so demoting them would have discarded real words like
   * `bioterrorisms`. See corrections/README.md.
   */
  words: { min: 345_000, max: 400_000 },

  /**
   * Intake shares, as a fraction of the list. The measured split on 2026-08-14,
   * after both demotions, was 175,501 / 131,226 / 31,243 / 7,327.
   *
   * `twl` and `pipeline` rose without gaining a single word: the denominator
   * fell by 33,594 across the two demotions. Worth remembering before reading a
   * share as growth.
   *
   * Only `pipeline` and `other` can move much on their own — promotion from the
   * invalid list adds to those two. **A rise in `synthetic` would mean generated
   * words were being added**, which has not happened since January 2026, and the
   * upper bound is kept tight for that reason. The lower bound leaves room for
   * the remaining 31,243 to go too, though the plurals among them are not
   * expected to.
   */
  intakeShare: {
    twl: { min: 0.46, max: 0.52 },
    pipeline: { min: 0.34, max: 0.39 },
    synthetic: { min: 0.0, max: 0.15 },
    other: { min: 0.0, max: 0.05 },
  },

  /**
   * 20,052 entries carry `unverified_llm_verdict: "invalid"` while listed as valid.
   *
   * This is not a data-integrity fault, and the field was renamed from `status`
   * in August 2026 so it stops reading like one. Every one of these was marked
   * invalid by a single LLM pass (Google Gemini 3 Flash Preview, December 2025)
   * that also passed 117,653 other words.
   *
   * It was measured rather than argued about. Of 400 sampled words,
   * Merriam-Webster could rule on only 18 — it has no entry for 95.8% of this
   * vocabulary — and of those 18 the LLM was wrong on 13, including
   * `clorazepate` and `antinociceptive`. The five it got right were all proper
   * nouns.
   *
   * So nothing has been moved on the strength of it, and nothing can be: no
   * source available to this project can adjudicate the other 95.8% at any
   * budget. See corrections/README.md.
   */
  llmSaysInvalid: { min: 19_000, max: 22_000 },

  /**
   * No word may be in both the valid and the invalid list. It is the one check
   * here with a single correct answer rather than a range.
   *
   * There were 150 until 2026-08-13, all of them words the nightly run had
   * promoted out of the invalid list without removing them from it. Every one
   * already carried a Merriam-Webster, MW Medical or Free Dictionary ruling in
   * its own entry, so all 150 were cleared against that stored evidence and
   * none was demoted. See corrections/ledger_stage1.csv.
   *
   * If this ever goes above zero again, the promotion path in
   * scripts/validate_invalid_list.py has regressed. Widening the bound is the
   * wrong fix.
   */
  alsoInvalid: { min: 0, max: 0 },

  /**
   * Zero, and now an invariant rather than a range.
   *
   * There were 190 until 2026-08-16 — 188 hyphenated and 2 accented — all of
   * them predating the form rule being written down anywhere. This build has in
   * fact been shipping a "Strictly a–z" download that excluded exactly those
   * 190 since before anyone noticed the list itself still carried them.
   *
   * They were deleted through corrections/ledger_form_rules.csv, and the form
   * rule `^[a-z]+$` is now enforced in scripts/word_validator.py, so nothing can
   * legitimately reappear here.
   *
   * If this ever goes above zero, an ingest path has stopped validating.
   * Widening the bound is the wrong fix — the same posture as `alsoInvalid`.
   */
  nonAlpha: { min: 0, max: 0 },

  /**
   * 6,680 words carry no date in any of the three fields that can hold one.
   *
   * Every one of them is in the `other` intake — the ~2% assembled before the
   * pipeline recorded dates at all. This is structural, not a parsing bug: it
   * was checked by grouping the undated words by intake, and the answer was
   * `{ other: 6680 }` exactly. If undated words start appearing in `twl`,
   * `pipeline` or `synthetic`, a field has been renamed and this should fail.
   */
  missingDate: { min: 5_000, max: 8_000 },

  /**
   * The date column is a bulk-load record, not a discovery timeline, and the
   * interface has to say so. 98.2% of the list carries one of three dates:
   * 2025-12-17 (131,226 pipeline words), 2026-01-10 (176,124 TWL) and
   * 2026-01-11 (64,837 synthetic). Everything else is the ~24 words promoted
   * one at a time since.
   *
   * Bounded loosely because the count grows by one on most promotion days.
   */
  distinctDates: { min: 15, max: 400 },
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
 * usually move together, and fixing them one build at a time wastes a 291 MB
 * download per attempt.
 */
export function assertExpectations(): void {
  if (tripped.length === 0) return;
  throw new Error(
    `The dataset no longer matches what this build was verified against:\n` +
      tripped.map((line) => `  - ${line}`).join('\n') +
      `\n\nRead tools/eol-build/src/expected.ts before widening a bound.`,
  );
}
