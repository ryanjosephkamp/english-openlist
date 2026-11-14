import { readdir, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { ATTESTERS, Attested, WordFlag, type AttesterKey } from '@eol/wordlist/format';
import { ATTESTING_SOURCES, PUBLISHED_INTAKES, type PublishedSource } from './sources.ts';
import type { Facts } from './facts.ts';
import { DAILY_METRICS_DIR, UPDATES_LOG } from './paths.ts';

/**
 * Aggregates for the charts, computed once at build time.
 *
 * The browser already holds every word, so it could compute all of this on
 * load. It does not, because these are the same numbers on every visit, and the
 * charts render on the server from this file, with no script.
 */

export type Stats = {
  readonly words: number;
  readonly lengths: readonly { length: number; count: number }[];
  /** First letters, `a` to `z`. */
  readonly firstLetters: readonly { letter: string; count: number }[];
  /** Every letter of every word, `a` to `z`. */
  readonly letters: readonly { letter: string; count: number }[];
  readonly letterTotal: number;
  /** Words the synthetic engine made. */
  readonly engine: number;
  readonly attestation: {
    /** Words per open source, in `ATTESTERS` order; a word counts under each source that lists it. */
    readonly sources: readonly { key: AttesterKey; label: string; url: string; count: number }[];
    /** Checked words by how many open sources list them: entry `k` counts the words exactly `k` list. */
    readonly bySourceCount: readonly number[];
    /** Words at least 1 open source lists. */
    readonly atLeastOne: number;
    /** Checked words no open source lists. */
    readonly none: number;
    /** Words not checked against the open sources yet. */
    readonly unchecked: number;
  };
  /** Words per published intake, and the words whose records name none; most of those came in with the list's first build. */
  readonly intakes: {
    readonly published: readonly { source: PublishedSource; label: string; count: number }[];
    readonly noSource: number;
  };
  readonly growth: Growth;
};

/**
 * The list's size day by day, from its daily statistics.
 *
 * 2 records cover it: the per-day length distributions kept in
 * `archive/daily-metrics/` (May 13 to August 11, 2026), whose counts sum to the
 * day's total, and the daily log `updates/updates_log.csv`, which records the
 * total from May 24 on. Where both cover a day the log is used.
 */
export type Growth = {
  readonly points: readonly { date: string; total: number }[];
  readonly first: { date: string; total: number };
  readonly last: { date: string; total: number };
  /** Days on which the total moved, with the change. */
  readonly events: readonly { date: string; delta: number; total: number }[];
  /** Days with no total recorded, between the first and the last. */
  readonly daysUnrecorded: number;
};

const NOT_RECORDED = new Set(['not recorded', 'unavailable', '']);

async function fromLog(): Promise<Map<string, number>> {
  const text = await readFile(UPDATES_LOG, 'utf8');
  const lines = text.trim().split('\n');
  const header = lines[0]!.split(',');
  const dateAt = header.indexOf('date');
  const totalAt = header.indexOf('total_valid_words_after');
  if (dateAt < 0 || totalAt < 0) throw new Error('updates_log.csv: a column moved');

  const out = new Map<string, number>();
  for (const line of lines.slice(1)) {
    // The notes column contains commas but is last, so a plain split still puts
    // the 2 columns this reads at stable indices.
    const cells = line.split(',');
    const raw = (cells[totalAt] ?? '').trim();
    if (NOT_RECORDED.has(raw) || !/^\d+$/.test(raw)) continue;
    out.set((cells[dateAt] ?? '').trim(), Number(raw));
  }
  return out;
}

async function fromDailyMetrics(): Promise<Map<string, number>> {
  const out = new Map<string, number>();
  const names = (await readdir(DAILY_METRICS_DIR)).filter((n) => n.endsWith('-word_length_distribution.csv'));
  for (const name of names) {
    const date = name.slice(0, 10);
    const lines = (await readFile(resolve(DAILY_METRICS_DIR, name), 'utf8')).trim().split('\n');
    if (lines[0]?.trim() !== 'word_length,count') throw new Error(`${name}: unexpected header`);
    let total = 0;
    for (const line of lines.slice(1)) {
      const count = Number(line.split(',')[1]);
      if (!Number.isInteger(count)) throw new Error(`${name}: a count is not a number`);
      total += count;
    }
    out.set(date, total);
  }
  return out;
}

const DAY = 86_400_000;

export async function buildGrowth(): Promise<Growth> {
  const merged = new Map([...(await fromDailyMetrics()), ...(await fromLog())]);
  const points = [...merged.entries()]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([date, total]) => ({ date, total }));
  if (points.length < 2) throw new Error('growth: fewer than 2 recorded days');

  const events: { date: string; delta: number; total: number }[] = [];
  for (let i = 1; i < points.length; i++) {
    const delta = points[i]!.total - points[i - 1]!.total;
    if (delta !== 0) events.push({ date: points[i]!.date, delta, total: points[i]!.total });
  }

  const first = points[0]!;
  const last = points[points.length - 1]!;
  const span = Math.round((Date.parse(last.date) - Date.parse(first.date)) / DAY) + 1;

  return { points, first, last, events, daysUnrecorded: span - points.length };
}

const bitCount = (n: number) => {
  let c = 0;
  for (let b = n; b; b &= b - 1) c++;
  return c;
};

export function buildStats(
  words: readonly Uint8Array[],
  facts: readonly (Facts | undefined)[],
  attested: Uint8Array,
  flags: Uint8Array,
  growth: Growth,
): Stats {
  const lengthCounts = new Map<number, number>();
  const first = new Array<number>(26).fill(0);
  const all = new Array<number>(26).fill(0);
  const perSource = new Array<number>(ATTESTERS.length).fill(0);
  const bySourceCount = new Array<number>(ATTESTERS.length + 1).fill(0);
  const perIntake = new Map<PublishedSource, number>();
  let unchecked = 0;
  let engine = 0;
  let noSource = 0;

  for (let i = 0; i < words.length; i++) {
    const bytes = words[i]!;
    // The form rule makes every word a to z, 1 byte a letter, so the byte
    // length is the character length.
    for (const b of bytes) {
      if (b < 0x61 || b > 0x7a) throw new Error(`word ${i} breaks the form rule ^[a-z]+$`);
      all[b - 0x61]!++;
    }
    const length = bytes.length;
    lengthCounts.set(length, (lengthCounts.get(length) ?? 0) + 1);
    first[bytes[0]! - 0x61]!++;

    const a = attested[i]!;
    if ((a & Attested.Unchecked) !== 0) unchecked++;
    else {
      bySourceCount[bitCount(a)]!++;
      for (let k = 0; k < ATTESTERS.length; k++) if ((a & (1 << k)) !== 0) perSource[k]!++;
    }
    if ((flags[i]! & WordFlag.Engine) !== 0) engine++;

    const intake = facts[i]?.intake ?? null;
    if (intake === null) noSource++;
    else perIntake.set(intake, (perIntake.get(intake) ?? 0) + 1);
  }

  const letter = (i: number) => String.fromCharCode(0x61 + i);

  return {
    words: words.length,
    lengths: [...lengthCounts.entries()].sort((a, b) => a[0] - b[0]).map(([length, count]) => ({ length, count })),
    firstLetters: first.map((count, i) => ({ letter: letter(i), count })),
    letters: all.map((count, i) => ({ letter: letter(i), count })),
    letterTotal: all.reduce((a, b) => a + b, 0),
    engine,
    attestation: {
      sources: ATTESTING_SOURCES.map((s, k) => ({ ...s, count: perSource[k]! })),
      bySourceCount,
      atLeastOne: words.length - unchecked - bySourceCount[0]!,
      none: bySourceCount[0]!,
      unchecked,
    },
    intakes: {
      published: PUBLISHED_INTAKES.map((p) => ({ source: p.source, label: p.label, count: perIntake.get(p.source) ?? 0 })),
      noSource,
    },
    growth,
  };
}
