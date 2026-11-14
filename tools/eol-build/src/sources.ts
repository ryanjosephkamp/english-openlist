import { ATTESTERS, Attested, attesterBit, type AttesterKey } from '@eol/wordlist/format';
import { ATTESTER_INFO } from '@eol/wordlist/sources';

/**
 * The 2 vocabularies a record may use, and nothing else.
 *
 * `attested_by` names the open sources that list the word: a property of the
 * word, published per word. `source` names the intake a record came in by, and
 * only these published intakes carry one; a record without it came in with the
 * list's first build. Of `source`, the site publishes per word only whether
 * the synthetic engine made the word, and the record's date.
 *
 * Both readers throw on a value outside their vocabulary, so a new label cannot
 * reach a public file before someone decides whether it may.
 */

/** The open sources, in the order `attested_by` lists them, with their names. */
export const ATTESTING_SOURCES: readonly { key: AttesterKey; label: string; url: string }[] = ATTESTERS.map((key) => ({
  key,
  ...ATTESTER_INFO[key],
}));

/** The published intakes: each `source` value a record may carry, with its name. */
export const PUBLISHED_INTAKES = [
  { source: 'synthetic_generation', label: 'The synthetic engine' },
  { source: 'authoritative_extracts', label: 'Domain extracts' },
  { source: 'extended_domain_sources', label: 'Extended domain sources' },
  { source: 'free-dictionary', label: 'The Free Dictionary API' },
  { source: 'invalid_list_recovery', label: 'The nightly run (promoted from the invalid list)' },
] as const;

export type PublishedSource = (typeof PUBLISHED_INTAKES)[number]['source'];

const SOURCES: ReadonlySet<string> = new Set(PUBLISHED_INTAKES.map((i) => i.source));
const ATTESTER_KEYS: ReadonlySet<string> = new Set(ATTESTERS);

/** A record's published intake, or null when it carries no `source`. */
export function intakeOf(record: { source?: unknown }): PublishedSource | null {
  if (record.source === undefined) return null;
  if (typeof record.source !== 'string' || !SOURCES.has(record.source)) {
    throw new Error(`unknown source: ${JSON.stringify(record.source)}`);
  }
  return record.source as PublishedSource;
}

/**
 * A record's ATTESTED byte: 1 bit per open source that lists the word, or
 * `Attested.Unchecked` when the record has no `attested_by` yet. An empty list
 * is a checked word that no open source lists, and is 0.
 */
export function attestedOf(record: { attested_by?: unknown }): number {
  const listed = record.attested_by;
  if (listed === undefined) return Attested.Unchecked;
  if (!Array.isArray(listed)) throw new Error(`attested_by is not a list: ${JSON.stringify(listed)}`);
  let bits = 0;
  for (const key of listed) {
    if (typeof key !== 'string' || !ATTESTER_KEYS.has(key)) {
      throw new Error(`unknown attested_by key: ${JSON.stringify(key)}`);
    }
    bits |= attesterBit(key as AttesterKey);
  }
  return bits;
}
