import { createReadStream } from 'node:fs';
import { chain } from 'stream-chain';
// stream-json is CommonJS and its modules export the class itself, so these
// arrive as constructors rather than as factory functions.
import Parser from 'stream-json/Parser.js';
import StreamObject from 'stream-json/streamers/StreamObject.js';
import { VALID_DICT } from './paths.ts';
import type { DecidedName } from '@eol/wordlist/format';
import { channelsOf, type Channels } from './channels.ts';

/** The intakes a record can be written by; internal to the build. */
export const INTAKE_NAMES = ['twl', 'pipeline', 'synthetic', 'other'] as const;
export type IntakeName = (typeof INTAKE_NAMES)[number];

/**
 * The facts the site needs about every word, reduced from a 291 MB file.
 *
 * `merged_valid_dict.json` is a single top-level object with 378,891 keys, and
 * entries are not uniformly shaped — the exploration found 31 distinct
 * top-level key-sets across four intakes. Nothing here assumes a field exists.
 *
 * Streamed rather than `JSON.parse`d. The parsed object graph is several GB,
 * which a CI runner will not reliably hold, and only three scalars per record
 * survive anyway.
 */
export type Facts = {
  /**
   * The intake the record was written by. Used for the build's own tripwires
   * and never written to a public file: 1 of its values names the tournament
   * word list, whose label the public files withhold.
   */
  readonly intake: IntakeName;
  /** What decided the word; see `DECIDED`. */
  readonly decided: DecidedName;
  /** The channels the word came in by, withheld labels taken out. */
  readonly channels: Channels;
  /** `YYYY-MM-DD`, or null when the record carries no usable date. */
  readonly added: string | null;
  /**
   * One LLM pass (Gemini 3 Flash, December 2025) called this word invalid while
   * it stayed in the valid list. Not a validation result — see
   * corrections/README.md. Kept because the site shows it, not because it decides
   * anything.
   */
  readonly llmSaysInvalid: boolean;
};

type Record_ = {
  source?: unknown;
  candidate_source?: unknown;
  manual_validation?: unknown;
  validation_source?: unknown;
  unverified_llm_verdict?: unknown;
  /** Pre-August-2026 name for the field above. */
  status?: unknown;
  added_date?: unknown;
  created_date?: unknown;
  validation_date?: unknown;
};

/**
 * Which intake a record arrived through.
 *
 * Ars Magna's equivalent tests `record.generation_method !== undefined` to
 * detect the synthetic group. That works, but only by accident of shape rather
 * than value: `generation_method` is present-and-`null` on all 64,837 synthetic
 * records, and `null !== undefined`. If the pipeline ever drops the key from a
 * synthetic record, or emits it on a non-synthetic one, that test silently
 * changes what counts as machine-generated. `source` is the field the dataset
 * card documents for this, so `source` is what this reads.
 */
export function intakeOf(record: Record_): IntakeName {
  const source = typeof record.source === 'string' ? record.source : null;
  if (source === 'twl_scrabble_dictionary') return 'twl';
  if (source === 'synthetic_generation') return 'synthetic';
  if (record.validation_source === 'verification_pipeline') return 'pipeline';
  return 'other';
}

/**
 * What decided a word, by the rule of the CEOL Universe's `model_or_engine`
 * column, so both projects count
 * the same words in each value.
 */
export function decidedOf(record: Record_): DecidedName {
  if (record.source === 'synthetic_generation') return 'engine';
  const manual = record.manual_validation;
  const named =
    !!manual && typeof manual === 'object' && !!(manual as Record<string, unknown>)['manual_validation_llm'];
  if (!named) return 'none';
  if (record.validation_source === 'verification_pipeline') return 'model_pipeline';
  if ('unverified_llm_verdict' in record && !('validation_source' in record)) return 'model_alone';
  return 'none';
}

/**
 * The date a word entered the list.
 *
 * Three different fields carry it depending on intake, and some are full
 * timestamps while others are bare dates, so everything is truncated to the day.
 */
export function addedOf(record: Record_): string | null {
  for (const value of [record.added_date, record.created_date, record.validation_date]) {
    if (typeof value !== 'string' || value.length < 10) continue;
    const day = value.slice(0, 10);
    if (/^\d{4}-\d{2}-\d{2}$/.test(day)) return day;
  }
  return null;
}

export async function loadFacts(
  onProgress?: (seen: number) => void,
): Promise<Map<string, Facts>> {
  const facts = new Map<string, Facts>();

  const pipeline = chain([
    createReadStream(VALID_DICT),
    new Parser({ jsonStreaming: false }),
    new StreamObject(),
  ]);

  let seen = 0;
  for await (const entry of pipeline as AsyncIterable<{ key: string; value: Record_ }>) {
    const record = entry.value ?? {};
    facts.set(entry.key, {
      intake: intakeOf(record),
      decided: decidedOf(record),
      channels: channelsOf(record),
      added: addedOf(record),
      // Accepts the old `status` name as well, so the data and this code can
      // land in either order without a window where the build reads a field
      // that does not exist yet and silently counts zero.
      llmSaysInvalid:
        (record.unverified_llm_verdict ?? record.status) === 'invalid',
    });
    if (++seen % 50_000 === 0) onProgress?.(seen);
  }

  return facts;
}

