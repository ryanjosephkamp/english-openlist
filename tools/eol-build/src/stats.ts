import { readFile } from 'node:fs/promises';
import { INTAKE_NAMES } from '@eol/wordlist/format';
import { UPDATES_LOG } from './paths.ts';

/**
 * Aggregates for the Shape page, computed once at build time.
 *
 * The browser already holds every word, so it could compute all of this on
 * load. It does not, because these are the same numbers on every visit and
 * folding them into ~14 KB of JSON is cheaper than 378,891 iterations on the
 * main thread while someone is trying to read.
 */

/** How many leading positions the letter-position matrix covers. */
export const POSITIONS = 12;

export type Stats = {
  readonly lengths: readonly { length: number; count: number }[];
  readonly letters: readonly { letter: string; count: number }[];
  readonly letterPosition: {
    readonly positions: number;
    /** 26 rows of `POSITIONS` counts, `a` first. */
    readonly counts: readonly (readonly number[])[];
    /** How many words are at least this long — the denominator for each column. */
    readonly columnTotals: readonly number[];
  };
  readonly intakeByLength: readonly {
    length: number;
    total: number;
    counts: readonly number[];
  }[];
  readonly growth: Growth;
};

/**
 * What the daily log actually supports.
 *
 * Deliberately not a series to plot. Over the 80 days the log records a total,
 * the list moved by 8 words on 7 days — 0.0021%. A zero-based line is a flat
 * line, and a line zoomed to the data turns 8 words into a dramatic climb. The
 * page states the figures and lists the events instead.
 */
export type Growth = {
  readonly recordedFrom: string;
  readonly recordedTo: string;
  readonly daysRecorded: number;
  readonly daysUnrecorded: number;
  readonly first: number;
  readonly last: number;
  readonly events: readonly { date: string; delta: number; total: number }[];
};

const NOT_RECORDED = new Set(['not recorded', 'unavailable', '']);

export async function buildGrowth(): Promise<Growth> {
  const text = await readFile(UPDATES_LOG, 'utf8');
  const lines = text.trim().split('\n');
  const header = lines[0]!.split(',');
  const dateAt = header.indexOf('date');
  const totalAt = header.indexOf('total_valid_words_after');

  const points: { date: string; total: number }[] = [];
  let unrecorded = 0;

  for (const line of lines.slice(1)) {
    // The notes column contains commas but is last, so a plain split still puts
    // the two columns this reads at stable indices.
    const cells = line.split(',');
    const raw = (cells[totalAt] ?? '').trim();
    if (NOT_RECORDED.has(raw) || !/^\d+$/.test(raw)) {
      unrecorded++;
      continue;
    }
    points.push({ date: (cells[dateAt] ?? '').trim(), total: Number(raw) });
  }

  const events: { date: string; delta: number; total: number }[] = [];
  for (let i = 1; i < points.length; i++) {
    const delta = points[i]!.total - points[i - 1]!.total;
    if (delta !== 0) events.push({ date: points[i]!.date, delta, total: points[i]!.total });
  }

  return {
    recordedFrom: points[0]?.date ?? '',
    recordedTo: points[points.length - 1]?.date ?? '',
    daysRecorded: points.length,
    daysUnrecorded: unrecorded,
    first: points[0]?.total ?? 0,
    last: points[points.length - 1]?.total ?? 0,
    events,
  };
}

export function buildStats(
  words: readonly Uint8Array[],
  intake: Uint8Array,
  growth: Growth,
): Stats {
  const lengthCounts = new Map<number, number>();
  const letterCounts = new Map<string, number>();
  const positionCounts = Array.from({ length: 26 }, () => new Array<number>(POSITIONS).fill(0));
  const columnTotals = new Array<number>(POSITIONS).fill(0);
  const intakeRows = new Map<number, number[]>();

  const decoder = new TextDecoder();

  for (let i = 0; i < words.length; i++) {
    const bytes = words[i]!;
    // Character length, not byte length: `norteño` is 7 letters and reporting 8
    // would put it in the wrong bucket on a chart about word length.
    const length = [...decoder.decode(bytes)].length;

    lengthCounts.set(length, (lengthCounts.get(length) ?? 0) + 1);

    const first = String.fromCharCode(bytes[0]!);
    letterCounts.set(first, (letterCounts.get(first) ?? 0) + 1);

    let row = intakeRows.get(length);
    if (!row) {
      row = new Array<number>(4).fill(0);
      intakeRows.set(length, row);
    }
    row[intake[i]!] = (row[intake[i]!] ?? 0) + 1;

    // Only a-z bytes land in the matrix. The 190 words carrying a hyphen or an
    // accent still contribute their other letters, and the column totals count
    // every word that reaches the position, so a share is never above 1.
    for (let p = 0; p < Math.min(bytes.length, POSITIONS); p++) {
      columnTotals[p]!++;
      const b = bytes[p]!;
      if (b >= 0x61 && b <= 0x7a) positionCounts[b - 0x61]![p]!++;
    }
  }

  return {
    lengths: [...lengthCounts.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([length, count]) => ({ length, count })),
    letters: [...letterCounts.entries()]
      .filter(([letter]) => /^[a-z]$/.test(letter))
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([letter, count]) => ({ letter, count })),
    letterPosition: { positions: POSITIONS, counts: positionCounts, columnTotals },
    intakeByLength: [...intakeRows.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([length, counts]) => ({
        length,
        total: counts.reduce((sum, n) => sum + n, 0),
        counts,
      })),
    growth,
  };
}

export const INTAKE_ORDER = INTAKE_NAMES;
