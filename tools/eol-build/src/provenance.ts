import { createReadStream } from 'node:fs';
import { mkdir, writeFile, rm } from 'node:fs/promises';
import { resolve } from 'node:path';
import { chain } from 'stream-chain';
import Parser from 'stream-json/Parser.js';
import StreamObject from 'stream-json/streamers/StreamObject.js';
import { VALID_DICT, DATA_DIR } from './paths.ts';

/**
 * Per-word provenance, sharded so a word page fetches ~1/512th of it.
 *
 * The source file is 291 MB and nobody is downloading that to look up one word.
 * Everything here is a reduction of one record to the facts a reader would
 * actually want: which sources attested it, which did not, what checked it, and
 * when.
 *
 * Strings are interned. `candidate_source` is 21 distinct values repeated across
 * 137,705 records, and `manual_validation_llm` is a single value repeated across
 * every one of them — storing indices into a table in the manifest rather than
 * the strings themselves is most of why this fits.
 */
export const SHARD_COUNT = 512;

/** Must match the browser's copy exactly or lookups land in the wrong shard. */
export function fnv1a(word: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < word.length; i++) {
    hash ^= word.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash >>> 0;
}

type Raw = Record<string, unknown>;

/**
 * One word's provenance, in the shape the shard stores.
 *
 * Single-letter keys because they repeat 378,891 times: `candidate_source`
 * spelled out costs more than the data it labels.
 */
export type Provenance = {
  /** Sources that attested it — indices into the manifest's source table. */
  a?: number[];
  /** Sources that called it unlikely. */
  u?: number[];
  /** Validation date, `YYYY-MM-DD`. */
  d?: string;
  /** Manual validation: [source, llm, date] as table indices, then status. */
  m?: [number, number, string, number];
  /** Advanced-validation confidence, 0–100. */
  c?: number;
  /** Statistical-validation confidence, 0–100. */
  s?: number;
  /** Proper-noun check: 1 = checked and not a proper noun, 2 = checked and is. */
  p?: number;
  /** Synthetic category, as a table index. */
  g?: number;
  /** The 222 Merriam-Webster records carry a real definition. */
  def?: string;
  pos?: string;
  pron?: string;
};

class Table {
  readonly values: string[] = [];
  readonly #index = new Map<string, number>();
  intern(value: string): number {
    const found = this.#index.get(value);
    if (found !== undefined) return found;
    const at = this.values.length;
    this.values.push(value);
    this.#index.set(value, at);
    return at;
  }
}

const STATUS = ['unknown', 'valid', 'invalid'];

function statusCode(value: unknown): number {
  if (value === 'valid') return 1;
  if (value === 'invalid') return 2;
  return 0;
}

function day(value: unknown): string | undefined {
  if (typeof value !== 'string' || value.length < 10) return undefined;
  const d = value.slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(d) ? d : undefined;
}

/**
 * Strip Merriam-Webster's markup from a definition or part of speech.
 *
 * The 222 MW records carry raw `{it}…{/it}` and `{et_link|a|b}` tokens. They are
 * meant for MW's own renderer and read as noise anywhere else.
 */
function clean(value: unknown): string | undefined {
  if (typeof value !== 'string' || !value.trim()) return undefined;
  const text = value
    .replace(/\{et_link\|[^|}]*\|([^}]*)\}/g, '$1')
    .replace(/\{d_link\|[^|}]*\|([^}]*)\}/g, '$1')
    .replace(/\{[^}]*\}/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  return text || undefined;
}

export type ProvenanceResult = {
  readonly sources: readonly string[];
  readonly manualSources: readonly string[];
  readonly llms: readonly string[];
  readonly categories: readonly string[];
  readonly statuses: readonly string[];
  readonly shardBytes: number;
  readonly largestShard: number;
  readonly withDefinition: number;
  readonly written: number;
};

export async function buildProvenance(
  onProgress?: (seen: number) => void,
): Promise<ProvenanceResult> {
  const sources = new Table();
  const manualSources = new Table();
  const llms = new Table();
  const categories = new Table();

  const shards: Record<string, Provenance>[] = Array.from({ length: SHARD_COUNT }, () => ({}));
  let seen = 0;
  let withDefinition = 0;

  const pipeline = chain([
    createReadStream(VALID_DICT),
    new Parser({ jsonStreaming: false }),
    new StreamObject(),
  ]);

  for await (const entry of pipeline as AsyncIterable<{ key: string; value: Raw }>) {
    const word = entry.key;
    const record = entry.value ?? {};
    const out: Provenance = {};

    const candidates = record['candidate_source'];
    if (Array.isArray(candidates)) {
      const attested: number[] = [];
      const unlikely: number[] = [];
      for (const raw of candidates) {
        if (typeof raw !== 'string') continue;
        // Every entry is an intake name suffixed `_valid` or `_unlikely`. The
        // suffix is the whole signal: a word can carry eight sources that all
        // say unlikely, which the dataset card warns about and which the word
        // page has to show rather than counting them as support.
        if (raw.endsWith('_unlikely')) unlikely.push(sources.intern(raw.slice(0, -9)));
        else if (raw.endsWith('_valid')) attested.push(sources.intern(raw.slice(0, -6)));
        else attested.push(sources.intern(raw));
      }
      if (attested.length) out.a = attested;
      if (unlikely.length) out.u = unlikely;
    }

    const date = day(record['validation_date']) ?? day(record['added_date']);
    if (date) out.d = date;

    const manual = record['manual_validation'];
    if (manual && typeof manual === 'object') {
      const m = manual as Raw;
      const source = m['manual_validation_source'];
      const llm = m['manual_validation_llm'];
      const when = day(m['manual_validation_date']);
      if (typeof source === 'string') {
        out.m = [
          manualSources.intern(source),
          typeof llm === 'string' ? llms.intern(llm) : -1,
          when ?? '',
          statusCode(m['manual_validation_status']),
        ];
      }
    }

    const advanced = record['advanced_validation'];
    if (advanced && typeof advanced === 'object') {
      const value = (advanced as Raw)['confidence'];
      if (typeof value === 'number') out.c = Math.round(value * 100);
    }

    const statistical = record['statistical_validation'];
    if (statistical && typeof statistical === 'object') {
      const value = (statistical as Raw)['confidence'];
      if (typeof value === 'number') out.s = Math.round(value * 100);
    }

    const properNoun = record['proper_noun_check'];
    if (properNoun && typeof properNoun === 'object') {
      const p = properNoun as Raw;
      if (p['checked'] === true) out.p = p['is_proper_noun'] === true ? 2 : 1;
    }

    const category = record['category'];
    if (typeof category === 'string') out.g = categories.intern(category);

    const definition = clean(record['definition']);
    if (definition) {
      out.def = definition;
      withDefinition++;
      const pos = clean(record['part_of_speech']);
      if (pos) out.pos = pos;
      const pron = clean(record['pronunciation']);
      if (pron) out.pron = pron;
    }

    // A record reduced to nothing is not written. Roughly the TWL intake, whose
    // whole story is "the tournament list has it" — already in the meta column.
    if (Object.keys(out).length > 0) shards[fnv1a(word) % SHARD_COUNT]![word] = out;

    if (++seen % 50_000 === 0) onProgress?.(seen);
  }

  const dir = resolve(DATA_DIR, 'prov');
  await rm(dir, { recursive: true, force: true });
  await mkdir(dir, { recursive: true });

  let shardBytes = 0;
  let largestShard = 0;
  let written = 0;

  for (let i = 0; i < SHARD_COUNT; i++) {
    const json = `${JSON.stringify(shards[i])}\n`;
    await writeFile(resolve(dir, `${i}.json`), json);
    const size = Buffer.byteLength(json);
    shardBytes += size;
    largestShard = Math.max(largestShard, size);
    written += Object.keys(shards[i]!).length;
  }

  return {
    sources: sources.values,
    manualSources: manualSources.values,
    llms: llms.values,
    categories: categories.values,
    statuses: STATUS,
    shardBytes,
    largestShard,
    withDefinition,
    written,
  };
}
