/**
 * The daily log's figures, read from `runs.json` when the site is built.
 */
import { runs, type Run } from './data';
import type { NightlyRun } from '../charts/Nightly';

const DAY = 86_400_000;
const parse = (iso: string) => Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)));
const iso = (t: number) => new Date(t).toISOString().slice(0, 10);

/** The runs, newest first, as the log lists them. */
export const newestFirst: readonly Run[] = [...runs].reverse();

/** What a run did, in a few words, for a list of runs. */
export function summary(run: Run): string {
  if (run.failed) return 'The run failed';
  const n = run.words.length;
  if (n > 0) return `${n} ${n === 1 ? 'word' : 'words'} added`;
  return run.recorded ? 'No words added' : 'No figures recorded';
}

export interface NightlyWindow {
  readonly from: string;
  readonly to: string;
  readonly runs: readonly NightlyRun[];
  /** words added in the window */
  readonly added: number;
  /** spans of 7 days or more with no run, first and last day */
  readonly gaps: readonly { from: string; to: string }[];
}

/**
 * The chart's window: every run from the first that promoted a word from the
 * invalid list to the last run.
 */
export function nightlyWindow(): NightlyWindow | null {
  const first = runs.findIndex((r) => (r.recorded?.promoted ?? 0) > 0);
  if (first < 0) return null;
  const window = runs.slice(first);
  const gaps: { from: string; to: string }[] = [];
  for (let i = 1; i < window.length; i++) {
    const after = parse(window[i - 1]!.date) + DAY;
    const before = parse(window[i]!.date) - DAY;
    if ((before - after) / DAY + 1 >= 7) gaps.push({ from: iso(after), to: iso(before) });
  }
  return {
    from: window[0]!.date,
    to: window[window.length - 1]!.date,
    runs: window.map((r) => ({ date: r.date, added: r.words.length, ...(r.failed ? { failed: true } : {}) })),
    added: window.reduce((n, r) => n + r.words.length, 0),
    gaps,
  };
}
