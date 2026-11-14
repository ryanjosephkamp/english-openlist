import { readdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { decodeMeta, decodeWords, wordAt } from '@eol/wordlist/decode';
import { WordFlag } from '@eol/wordlist/format';
import { DATA_DIR, POSTS_DIR } from './paths.ts';
import type { Growth } from './stats.ts';

/**
 * The daily log: 1 entry for each nightly run, read from the run's own post in
 * `_posts/` and checked against the list.
 *
 * A run's words are the words on the list that carry its date, and the words
 * its post names that are on the list with no date at all: a record carries a
 * date only when it names a published intake. The post is the run's own record,
 * so its figures are kept as the run wrote them, and a word it names that the
 * list dates to another day, or does not hold, is reported rather than dropped.
 */

/** How a word of a run got on: the post's own sections, or only the list's date. */
export type RunHow = 'promoted' | 'discovered' | 'dated';

export type RunWord = {
  readonly word: string;
  /** Which open sources list the word: its ATTESTED byte; see `Attested`. */
  readonly attested: number;
  /** The synthetic engine made the word. */
  readonly engine: boolean;
  readonly how: RunHow;
};

export type Run = {
  /** `YYYY-MM-DD`, the date in the post's file name. */
  readonly date: string;
  /** When the run wrote its post, ISO 8601, or null when the post does not say. */
  readonly at: string | null;
  /** The post's file name in `_posts/`. */
  readonly post: string;
  /** The words on the list that carry this date. */
  readonly words: readonly RunWord[];
  /** Words the post names that the list does not carry with this date. */
  readonly missing: readonly string[];
  /** The post's own figures, or null where it recorded none. */
  readonly recorded: {
    readonly added: number;
    readonly promoted: number;
    readonly discovered: number;
    /** Invalid entries after the run; null where the post recorded 0. */
    readonly invalid: number | null;
  } | null;
  /** The post recorded the list as 0 words: the run failed before it read the list. */
  readonly failed: boolean;
  /** The list's size after the run and on the recorded day before it, from the daily statistics. */
  readonly total: number | null;
  readonly before: number | null;
  /** The whole list's shape after the run, where the post recorded one that adds up to its total. */
  readonly lengths: readonly { length: number; count: number }[] | null;
  readonly firstLetters: readonly { letter: string; count: number }[] | null;
};

/** A day with more dated words than this is a bulk load, not a night's run. */
export const MOST_WORDS = 500;

const DAILY = /^(\d{4}-\d{2}-\d{2})-daily-update\.md$/;
const CHART_DATA = /<script id="daily-chart-data" type="application\/json">([\s\S]*?)<\/script>/;

function figure(body: string, label: string): number | null {
  // The generator writes these as `- **Total valid words now:** **345,166**`.
  const found = new RegExp(`\\*\\*${label}:\\*\\*\\s*\\**([^*\\n]+)`).exec(body);
  const raw = found?.[1]?.trim().replace(/,/g, '') ?? '';
  return /^\d+$/.test(raw) ? Number(raw) : null;
}

function block(body: string, heading: string): string[] {
  const found = new RegExp(`### ${heading}\\s*\`\`\`text\\n([\\s\\S]*?)\`\`\``).exec(body);
  return found ? found[1]!.split(/\s+/).filter(Boolean) : [];
}

export type Post = {
  readonly date: string;
  readonly file: string;
  readonly at: string | null;
  readonly added: number | null;
  readonly promoted: number | null;
  readonly discovered: number | null;
  readonly total: number | null;
  readonly invalid: number | null;
  readonly promotedWords: readonly string[];
  readonly discoveredWords: readonly string[];
  readonly chart: { wordLength?: { labels: string[]; values: number[] }; startingLetter?: { labels: string[]; values: number[] } } | null;
};

export function parsePost(file: string, text: string): Post {
  const date = DAILY.exec(file)?.[1];
  if (!date) throw new Error(`${file}: not a daily post`);
  const at = /\*\*Generated automatically at (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) UTC\*\*/.exec(text);
  let chart: Post['chart'] = null;
  const json = CHART_DATA.exec(text)?.[1];
  if (json) {
    try {
      chart = JSON.parse(json) as Post['chart'];
    } catch {
      chart = null;
    }
  }
  return {
    date,
    file,
    at: at ? `${at[1]}T${at[2]}Z` : null,
    added: figure(text, 'Total words added today'),
    promoted: figure(text, 'Words promoted from invalid list'),
    discovered: figure(text, 'New words discovered today'),
    total: figure(text, 'Total valid words now'),
    invalid: figure(text, 'Total invalid entries tracked'),
    promotedWords: block(text, 'Words Promoted Today'),
    discoveredWords: block(text, 'New Words Discovered Today'),
    chart,
  };
}

export async function loadPosts(): Promise<Post[]> {
  const files = (await readdir(POSTS_DIR)).filter((f) => DAILY.test(f)).sort();
  return Promise.all(files.map(async (f) => parsePost(f, await readFile(resolve(POSTS_DIR, f), 'utf8'))));
}

/** The list as the build wrote it: each dated word under its date, with its ATTESTED byte and engine flag. */
export type DatedWord = { readonly word: string; readonly attested: number; readonly engine: boolean };
export type Dated = ReadonlyMap<string, readonly DatedWord[]>;
/** Words on the list that carry no date, by word. */
export type Undated = ReadonlyMap<string, DatedWord>;

/** The list's dated words, and those of `named` that it holds with no date. */
export async function loadDated(named: ReadonlySet<string>): Promise<{ dated: Dated; undated: Undated }> {
  const manifest = JSON.parse(await readFile(resolve(DATA_DIR, 'manifest.json'), 'utf8')) as {
    dateTable: string[];
    files: Record<string, { name: string }>;
  };
  const table = decodeWords(new Uint8Array(await readFile(resolve(DATA_DIR, manifest.files['words']!.name))));
  const meta = decodeMeta(new Uint8Array(await readFile(resolve(DATA_DIR, manifest.files['meta']!.name))));
  const out = new Map<string, DatedWord[]>();
  const undated = new Map<string, DatedWord>();
  for (let i = 0; i < table.count; i++) {
    const date = manifest.dateTable[meta.added[i]!];
    const word = wordAt(table, i);
    const entry = { word, attested: meta.attested[i]!, engine: (meta.flags[i]! & WordFlag.Engine) !== 0 };
    if (!date) {
      if (named.has(word)) undated.set(word, entry);
      continue;
    }
    let day = out.get(date);
    if (!day) out.set(date, (day = []));
    day.push(entry);
  }
  return { dated: out, undated };
}

function shape(post: Post): Pick<Run, 'lengths' | 'firstLetters'> {
  const wl = post.chart?.wordLength;
  const sl = post.chart?.startingLetter;
  const none = { lengths: null, firstLetters: null };
  if (!wl || !sl || post.total === null || post.total === 0) return none;
  const sum = (v: readonly number[]) => v.reduce((a, b) => a + b, 0);
  // A distribution that does not add up to the post's own total describes some
  // other list, and is left out rather than shown beside the wrong figure.
  if (sum(wl.values) !== post.total || sum(sl.values) !== post.total) return none;
  return {
    lengths: wl.labels.map((l, i) => ({ length: Number(l), count: wl.values[i]! })),
    firstLetters: sl.labels.map((l, i) => ({ letter: l.toLowerCase(), count: sl.values[i]! })),
  };
}

export function buildRuns(
  posts: readonly Post[],
  dated: Dated,
  growth: Pick<Growth, 'points'>,
  undated: Undated = new Map(),
): Run[] {
  const totals = growth.points;
  return posts.map((post) => {
    const named = new Map<string, RunHow>();
    for (const w of post.discoveredWords) named.set(w, 'discovered');
    for (const w of post.promotedWords) named.set(w, 'promoted');

    const onDay = dated.get(post.date) ?? [];
    if (onDay.length > MOST_WORDS) throw new Error(`${post.date}: ${onDay.length} words carry a run's date`);
    const words: RunWord[] = onDay.map(({ word, attested, engine }) => ({ word, attested, engine, how: named.get(word) ?? 'dated' }));
    const listed = new Set(onDay.map((w) => w.word));
    const missing: string[] = [];
    for (const [word, how] of [...named.entries()].sort((a, b) => a[0].localeCompare(b[0]))) {
      if (listed.has(word)) continue;
      const held = undated.get(word);
      if (held) words.push({ word, attested: held.attested, engine: held.engine, how });
      else missing.push(word);
    }

    const failed = post.total === 0;
    const recorded =
      post.added === null || post.promoted === null || post.discovered === null || failed
        ? null
        : { added: post.added, promoted: post.promoted, discovered: post.discovered, invalid: post.invalid || null };

    const at = totals.findIndex((p) => p.date === post.date);
    const total = at >= 0 && !failed ? totals[at]!.total : null;
    const before = at > 0 && !failed ? totals[at - 1]!.total : null;

    return { date: post.date, at: post.at, post: post.file, words, missing, recorded, failed, total, before, ...shape(post) };
  });
}

export async function writeRuns(growth: Pick<Growth, 'points'>): Promise<Run[]> {
  const posts = await loadPosts();
  const named = new Set(posts.flatMap((p) => [...p.promotedWords, ...p.discoveredWords]));
  const { dated, undated } = await loadDated(named);
  const runs = buildRuns(posts, dated, growth, undated);
  await writeFile(resolve(DATA_DIR, 'runs.json'), `${JSON.stringify(runs)}\n`);
  return runs;
}

// `node src/runs.ts` rewrites only the daily log, from the list already built.
if (import.meta.main) {
  const { buildGrowth } = await import('./stats.ts');
  const runs = await writeRuns(await buildGrowth());
  const words = runs.reduce((n, r) => n + r.words.length, 0);
  const missing = runs.reduce((n, r) => n + r.missing.length, 0);
  console.log(`runs.json  ${runs.length} runs, ${words} words added by a run, ${missing} named by a post but not counted`);
}
