/**
 * The build's data, read when the site is built. Every figure on these pages
 * comes from these files, which `tools/eol-build` writes from the dataset.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

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

export type DecidedName = 'none' | 'model_pipeline' | 'model_alone' | 'engine';
export const DECIDED_ORDER: readonly DecidedName[] = ['none', 'model_pipeline', 'model_alone', 'engine'];

/** What decided a word, in the words the CEOL Universe uses for the same values. */
export const DECIDED_LABEL: Readonly<Record<DecidedName, string>> = {
  none: 'No model or engine',
  model_pipeline: 'A pipeline that used a language model',
  model_alone: "A language model's verdict alone",
  engine: 'The synthetic engine',
};

export const DECIDED_WHAT: Readonly<Record<DecidedName, string>> = {
  none: 'a list, a dictionary API, or a domain extract; no language model and no engine',
  model_pipeline: 'passed the verification pipeline, a multi-stage check that used a language model',
  model_alone: "rests on a language model's verdict alone",
  engine: "made by the list's synthetic engine",
};

export interface Manifest {
  readonly builtAt: string;
  readonly revision: string | null;
  readonly wordCount: number;
  readonly dateTable: readonly string[];
  readonly decidedCounts: Readonly<Record<DecidedName, number>>;
  readonly llmSaysInvalid: number;
  readonly invalidCount: number;
  readonly alsoInvalid: number;
  readonly missingDate: number;
  readonly bulkDates: readonly { date: string; count: number }[];
  readonly addedSingly: number;
  readonly downloads: readonly { file: string; label: string; note: string; words: number; bytes: number }[];
  readonly files: Readonly<Record<string, { name: string; bytes: number; brotliBytes: number }>>;
}

export interface Stats {
  readonly words: number;
  readonly lengths: readonly { length: number; count: number }[];
  readonly firstLetters: readonly { letter: string; count: number }[];
  readonly letters: readonly { letter: string; count: number }[];
  readonly letterTotal: number;
  readonly decided: Readonly<Record<DecidedName, number>>;
  readonly decidedByLength: readonly { length: number; counts: readonly number[] }[];
  readonly channels: {
    readonly published: readonly { key: string; label: string; kind: string; count: number }[];
    readonly withPublished: number;
  };
  readonly growth: {
    readonly points: readonly { date: string; total: number }[];
    readonly first: { date: string; total: number };
    readonly last: { date: string; total: number };
    readonly events: readonly { date: string; delta: number; total: number }[];
    readonly daysUnrecorded: number;
  };
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

if (stats.words !== manifest.wordCount) throw new Error('stats.json and manifest.json describe different lists');

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
export function hfFile(path: string): string {
  return `${HF}/resolve/${manifest.revision ?? 'main'}/${path}`;
}
