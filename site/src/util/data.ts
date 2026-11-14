/**
 * The build's data, read when the site is built. Every figure on these pages
 * comes from these files, which `tools/eol-build` writes from the dataset.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { AttesterKey } from '@eol/wordlist/format';

// Read from the site's folder: the build runs there, and this module runs from
// a bundled chunk, so its own address says nothing about where the data is.
const dir = resolve(process.cwd(), 'public/data');

function read<T>(name: string): T {
  const path = resolve(dir, name);
  try {
    return JSON.parse(readFileSync(path, 'utf8')) as T;
  } catch (cause) {
    throw new Error(`${name} is missing: run \`pnpm data:build\` first`, { cause });
  }
}

export { NOTICES_URL } from '@eol/wordlist/sources';

export interface Manifest {
  readonly builtAt: string;
  readonly revision: string | null;
  /** When that revision was committed on Hugging Face; null for a build from a local copy. */
  readonly publishedAt: string | null;
  readonly wordCount: number;
  readonly dateTable: readonly string[];
  /** Words the synthetic engine made. */
  readonly engine: number;
  readonly invalidCount: number;
  readonly alsoInvalid: number;
  /** Words with a date, and without one. */
  readonly dated: number;
  readonly missingDate: number;
  /** Days that date more words than a night's run adds. */
  readonly bulkDates: readonly { date: string; count: number }[];
  readonly downloads: readonly { file: string; label: string; note: string; words: number; bytes: number }[];
  readonly files: Readonly<Record<string, { name: string; bytes: number; brotliBytes: number }>>;
}

export interface Stats {
  readonly words: number;
  readonly lengths: readonly { length: number; count: number }[];
  readonly firstLetters: readonly { letter: string; count: number }[];
  readonly letters: readonly { letter: string; count: number }[];
  readonly letterTotal: number;
  readonly engine: number;
  readonly attestation: {
    /** Words per open source; a word counts under each source that lists it. */
    readonly sources: readonly { key: AttesterKey; label: string; url: string; count: number }[];
    /** Checked words by how many open sources list them: entry `k` counts the words exactly `k` list. */
    readonly bySourceCount: readonly number[];
    readonly atLeastOne: number;
    readonly none: number;
    readonly unchecked: number;
  };
  /** Words per published intake, and the words whose records name none; most of those came in with the list's first build. */
  readonly intakes: {
    readonly published: readonly { source: string; label: string; count: number }[];
    readonly noSource: number;
  };
  readonly growth: {
    readonly points: readonly { date: string; total: number }[];
    readonly first: { date: string; total: number };
    readonly last: { date: string; total: number };
    readonly events: readonly { date: string; delta: number; total: number }[];
    readonly daysUnrecorded: number;
  };
}

/** 1 nightly run, as `tools/eol-build/src/runs.ts` writes it. */
export type RunHow = 'promoted' | 'discovered' | 'dated';
export interface Run {
  readonly date: string;
  readonly at: string | null;
  readonly post: string;
  /** `attested` is the word's ATTESTED byte; see `Attested`. */
  readonly words: readonly { word: string; attested: number; engine: boolean; how: RunHow }[];
  readonly missing: readonly string[];
  readonly recorded: { added: number; promoted: number; discovered: number; invalid: number | null } | null;
  readonly failed: boolean;
  readonly total: number | null;
  readonly before: number | null;
  readonly lengths: readonly { length: number; count: number }[] | null;
  readonly firstLetters: readonly { letter: string; count: number }[] | null;
}

export interface LedgerCount {
  readonly ledger: string;
  readonly action: string;
  readonly date: string;
  readonly count: number;
}

export const manifest = read<Manifest>('manifest.json');
export const stats = read<Stats>('stats.json');
export const record = read<LedgerCount[]>('record.json');
/** The runs, oldest first. */
export const runs = read<Run[]>('runs.json');

/** A run's page in the daily log. */
export const runHref = (date: string) => `/blog/${date}/`;

if (stats.words !== manifest.wordCount) throw new Error('stats.json and manifest.json describe different lists');

/** The day the list on this site was published: its revision's commit date, or the nightly log's last day. */
export const publishedOn = manifest.publishedAt?.slice(0, 10) ?? stats.growth.last.date;

export const fmt = (n: number) => Math.round(n).toLocaleString('en-US');

/** The ledger rows with this action, summed over the named ledgers (all when none). */
export function moved(action: string, ...ledgers: string[]): number {
  return record
    .filter((r) => r.action === action && (ledgers.length === 0 || ledgers.includes(r.ledger)))
    .reduce((sum, r) => sum + r.count, 0);
}

/** The dataset on Hugging Face, and its files at the revision this site was built from. */
export const HF = 'https://huggingface.co/datasets/ryanjosephkamp/english-openlist';
export const REPO = 'https://github.com/ryanjosephkamp/english-openlist';
/** Where a correction or a request to remove something goes. */
export const CONTACT = 'ryanjosephkamp@gmail.com';
export function hfFile(path: string): string {
  return `${HF}/resolve/${manifest.revision ?? 'main'}/${path}`;
}
