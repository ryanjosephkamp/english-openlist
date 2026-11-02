import { readdir, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { DECIDED_NAMES, type DecidedName } from '@eol/wordlist/format';
import { CHANNELS, type ChannelKey } from './channels.ts';
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
  readonly decided: Readonly<Record<DecidedName, number>>;
  /** For each length, the count of each `DECIDED` value, in `DECIDED_NAMES` order. */
  readonly decidedByLength: readonly { length: number; counts: readonly number[] }[];
  readonly channels: {
    /** Words per published channel; a word counts under each of its channels. */
    readonly published: readonly { key: ChannelKey; label: string; kind: string; count: number }[];
    /** Words with at least 1 published channel. */
    readonly withPublished: number;
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

/**
 * The counts the build reports in its log and never writes to a public file:
 * the words whose every channel is withheld would chart the withheld channels
 * in all but name.
 */
export type Unpublished = { readonly withheld: number; readonly unrecorded: number };

export function buildStats(
  words: readonly Uint8Array[],
  facts: readonly (Facts | undefined)[],
  decided: Uint8Array,
  growth: Growth,
): { stats: Stats; unpublished: Unpublished } {
  const lengthCounts = new Map<number, number>();
  const first = new Array<number>(26).fill(0);
  const all = new Array<number>(26).fill(0);
  const byLength = new Map<number, number[]>();
  const decidedCounts = new Array<number>(DECIDED_NAMES.length).fill(0);
  const channelCounts = new Map<ChannelKey, number>();
  let withheld = 0;
  let unrecorded = 0;
  let withPublished = 0;

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

    const d = decided[i]!;
    decidedCounts[d]!++;
    let row = byLength.get(length);
    if (!row) byLength.set(length, (row = new Array<number>(DECIDED_NAMES.length).fill(0)));
    row[d]!++;

    const channels = facts[i]?.channels ?? { kind: 'unrecorded' as const };
    if (channels.kind === 'published') {
      withPublished++;
      for (const key of channels.keys) channelCounts.set(key, (channelCounts.get(key) ?? 0) + 1);
    } else if (channels.kind === 'withheld') withheld++;
    else unrecorded++;
  }

  const letter = (i: number) => String.fromCharCode(0x61 + i);

  const stats: Stats = {
    words: words.length,
    lengths: [...lengthCounts.entries()].sort((a, b) => a[0] - b[0]).map(([length, count]) => ({ length, count })),
    firstLetters: first.map((count, i) => ({ letter: letter(i), count })),
    letters: all.map((count, i) => ({ letter: letter(i), count })),
    letterTotal: all.reduce((a, b) => a + b, 0),
    decided: Object.fromEntries(DECIDED_NAMES.map((name, i) => [name, decidedCounts[i]!])) as Record<DecidedName, number>,
    decidedByLength: [...byLength.entries()].sort((a, b) => a[0] - b[0]).map(([length, counts]) => ({ length, counts })),
    channels: {
      published: CHANNELS.map((c) => ({ key: c.key, label: c.label, kind: c.kind, count: channelCounts.get(c.key) ?? 0 })),
      withPublished,
    },
    growth,
  };
  return { stats, unpublished: { withheld, unrecorded } };
}
