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
  /** 378,891 on 2026-08-13. Grows by roughly one a day; shrinking is the alarm. */
  words: { min: 378_800, max: 400_000 },

  /**
   * Intake shares, as a fraction of the list. The dataset card documents
   * ~46/35/17/2 and the measured split on 2026-08-13 was
   * 175,501 / 131,226 / 64,837 / 7,327.
   *
   * Only `pipeline` and `other` can move much: promotion from the invalid list
   * adds to those two. A jump in `synthetic` would mean generated words were
   * being added, which has not happened since January 2026.
   */
  intakeShare: {
    twl: { min: 0.44, max: 0.48 },
    pipeline: { min: 0.33, max: 0.37 },
    synthetic: { min: 0.15, max: 0.19 },
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

  /** 190 words contain something outside `a-z` — 188 hyphenated, 2 accented. */
  nonAlpha: { min: 150, max: 250 },

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
