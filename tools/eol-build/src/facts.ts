import { createReadStream } from 'node:fs';
import { chain } from 'stream-chain';
// stream-json is CommonJS and its modules export the class itself, so these
// arrive as constructors rather than as factory functions.
import Parser from 'stream-json/Parser.js';
import StreamObject from 'stream-json/streamers/StreamObject.js';
import { VALID_DICT } from './paths.ts';
import { attestedOf, intakeOf, type PublishedSource } from './sources.ts';

/**
 * The facts the build needs about every word, reduced from
 * `merged_valid_dict.json`.
 *
 * Every record carries `word`, `length`, and `attested_by`; a record of a
 * published intake also carries `source`, and usually `added_date`. Nothing
 * here assumes an optional field exists.
 *
 * Streamed rather than `JSON.parse`d, so the build's memory does not grow with
 * the file.
 */
export type Facts = {
  /** Which open sources list the word; see `Attested`. */
  readonly attested: number;
  /** The record's published intake, or null when it names none. */
  readonly intake: PublishedSource | null;
  /** The record's `added_date`, `YYYY-MM-DD`, or null when it has none. */
  readonly added: string | null;
};

/** The fields a record may carry. */
export const RECORD_FIELDS: ReadonlySet<string> = new Set(['word', 'length', 'attested_by', 'source', 'added_date']);

type Record_ = {
  source?: unknown;
  attested_by?: unknown;
  added_date?: unknown;
};

/** A record's date. Throws on a value that is not `YYYY-MM-DD`. */
export function addedOf(record: Record_): string | null {
  const value = record.added_date;
  if (value === undefined) return null;
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    throw new Error(`added_date is not YYYY-MM-DD: ${JSON.stringify(value)}`);
  }
  return value;
}

export async function loadFacts(onProgress?: (seen: number) => void): Promise<{
  facts: Map<string, Facts>;
  /** Fields found outside `RECORD_FIELDS`, with the number of records carrying each. */
  unexpected: Map<string, number>;
  /** Records carrying at least 1 field outside `RECORD_FIELDS`. */
  unexpectedRecords: number;
}> {
  const facts = new Map<string, Facts>();
  const unexpected = new Map<string, number>();
  let unexpectedRecords = 0;

  const pipeline = chain([
    createReadStream(VALID_DICT),
    new Parser({ jsonStreaming: false }),
    new StreamObject(),
  ]);

  let seen = 0;
  for await (const entry of pipeline as AsyncIterable<{ key: string; value: Record_ }>) {
    const record = entry.value ?? {};
    let odd = false;
    for (const field of Object.keys(record)) {
      if (RECORD_FIELDS.has(field)) continue;
      unexpected.set(field, (unexpected.get(field) ?? 0) + 1);
      odd = true;
    }
    if (odd) unexpectedRecords++;
    try {
      facts.set(entry.key, { attested: attestedOf(record), intake: intakeOf(record), added: addedOf(record) });
    } catch (cause) {
      throw new Error(`record "${entry.key}": ${cause instanceof Error ? cause.message : String(cause)}`, { cause });
    }
    if (++seen % 50_000 === 0) onProgress?.(seen);
  }

  return { facts, unexpected, unexpectedRecords };
}
