import type { WordTable, MetaTable } from './decode.ts';
import { prefixRange, includesAt, endsWithAt, wordAt } from './decode.ts';
import { INTAKE, type IntakeName } from './format.ts';

export type MatchMode = 'prefix' | 'contains' | 'suffix' | 'pattern' | 'regex';

export type SortKey = 'alpha' | 'length' | 'added';

/**
 * Which characters a word is allowed to contain.
 *
 * This is a filter on the whole word, not on its first letter, because no word
 * in the list *starts* with anything but `a`–`z`. The 188 hyphenated entries
 * carry their hyphen internally (`ad-lib`, `across-the-board`) and both accented
 * words carry the accent internally (`norteño`, `peléan`) — which the byte
 * ordering proves: `-` is 0x2D and would sort ahead of `a`, and the list begins
 * with `a`.
 */
export type Charset = 'any' | 'alpha' | 'hyphen' | 'accent';

export type Query = {
  readonly text: string;
  readonly mode: MatchMode;
  readonly minLength: number;
  readonly maxLength: number;
  /** Empty means every intake. */
  readonly intakes: readonly IntakeName[];
  /** Empty means every first letter. Single lowercase letters only. */
  readonly letters: readonly string[];
  readonly charset: Charset;
  readonly sort: SortKey;
  readonly descending: boolean;
  /** Include entries whose own metadata records `status: "invalid"`. */
  readonly includeContested: boolean;
};

export const DEFAULT_QUERY: Query = {
  text: '',
  mode: 'prefix',
  minLength: 1,
  maxLength: 47,
  intakes: [],
  letters: [],
  charset: 'any',
  sort: 'alpha',
  descending: false,
  includeContested: true,
};

/** `status: "invalid"` — see WordFlag.LlmSaysInvalid. */
const FLAG_STATUS_INVALID = 1 << 0;

export type QueryResult = {
  /** Word indices, in display order. */
  readonly indices: Uint32Array;
  /** Wall-clock cost of the scan, for the interface to state honestly. */
  readonly millis: number;
  /**
   * Set when the query could not run as written — an unparseable regex, say.
   * The interface says so rather than showing zero results as if that were an
   * answer.
   */
  readonly error: string | null;
};

const encoder = new TextEncoder();

/**
 * Translate a glob pattern to a matcher over UTF-8 bytes.
 *
 * `_` matches exactly one byte, `*` matches any run. Crossword notation, and
 * the reason it is byte-wise rather than regex-over-strings: the scan runs over
 * every one of 378,891 words on each keystroke, and decoding each to a string
 * first costs more than the match does.
 *
 * `_` matching a *byte* rather than a character is a real limitation for the
 * two accented words — `norte_o` will not match `norteño`, whose `ñ` is two
 * bytes. That affects 2 words out of 378,891, and the alternative is decoding
 * all of them on every keystroke.
 */
function globMatcher(pattern: string): (bytes: Uint8Array, start: number, length: number) => boolean {
  const p = encoder.encode(pattern);

  return (bytes, start, length) => {
    // Classic two-pointer glob match with backtracking on the last `*`.
    let pi = 0;
    let si = 0;
    let starP = -1;
    let starS = 0;

    while (si < length) {
      const pc = pi < p.length ? p[pi] : undefined;
      if (pc !== undefined && (pc === 0x5f /* _ */ || pc === bytes[start + si])) {
        pi++;
        si++;
      } else if (pc === 0x2a /* * */) {
        starP = pi++;
        starS = si;
      } else if (starP !== -1) {
        pi = starP + 1;
        si = ++starS;
      } else {
        return false;
      }
    }
    while (pi < p.length && p[pi] === 0x2a) pi++;
    return pi === p.length;
  };
}

export function runQuery(table: WordTable, meta: MetaTable, query: Query): QueryResult {
  const started = performance.now();

  const text = query.text.trim().toLowerCase();

  // Prefix is the only mode that narrows before scanning: the list is sorted, so
  // every match is one contiguous run and two binary searches find its bounds.
  let from = 0;
  let to = table.count;
  let needle: Uint8Array | null = null;
  let glob: ReturnType<typeof globMatcher> | null = null;
  let regex: RegExp | null = null;

  if (text) {
    switch (query.mode) {
      case 'prefix': {
        [from, to] = prefixRange(table, encoder.encode(text));
        break;
      }
      case 'contains':
      case 'suffix':
        needle = encoder.encode(text);
        break;
      case 'pattern':
        glob = globMatcher(text);
        break;
      case 'regex':
        try {
          regex = new RegExp(text, 'u');
        } catch (cause) {
          return {
            indices: new Uint32Array(0),
            millis: performance.now() - started,
            error: cause instanceof Error ? cause.message : 'not a valid regular expression',
          };
        }
        break;
    }
  }

  const intakeMask = intakeBits(query.intakes);
  const letterSet = letterBytes(query.letters);

  const out = new Uint32Array(to - from);
  let n = 0;

  for (let i = from; i < to; i++) {
    const length = table.lengths[i]!;
    if (length < query.minLength || length > query.maxLength) continue;

    if (intakeMask !== 0b1111 && (intakeMask & (1 << meta.intake[i]!)) === 0) continue;
    if (!query.includeContested && (meta.flags[i]! & FLAG_STATUS_INVALID) !== 0) continue;

    if (letterSet !== null && !letterSet.has(table.bytes[table.offsets[i]!]!)) continue;

    if (query.charset !== 'any' && !matchesCharset(table, i, query.charset)) continue;

    if (needle !== null) {
      const ok =
        query.mode === 'suffix' ? endsWithAt(table, i, needle) : includesAt(table, i, needle);
      if (!ok) continue;
    } else if (glob !== null) {
      if (!glob(table.bytes, table.offsets[i]!, length)) continue;
    } else if (regex !== null) {
      if (!regex.test(wordAt(table, i))) continue;
    }

    out[n++] = i;
  }

  const indices = out.subarray(0, n);
  sortIndices(indices, table, meta, query);

  return { indices, millis: performance.now() - started, error: null };
}

function intakeBits(intakes: readonly IntakeName[]): number {
  if (intakes.length === 0) return 0b1111;
  let mask = 0;
  for (const name of intakes) mask |= 1 << INTAKE[name];
  return mask;
}

/** First-byte set for the letter filter. Every word starts with `a`–`z`. */
function letterBytes(letters: readonly string[]): Set<number> | null {
  if (letters.length === 0) return null;
  const set = new Set<number>();
  for (const letter of letters) set.add(letter.charCodeAt(0));
  return set;
}

function matchesCharset(table: WordTable, index: number, charset: Charset): boolean {
  const start = table.offsets[index]!;
  const end = start + table.lengths[index]!;

  let hyphen = false;
  let accent = false;
  for (let i = start; i < end; i++) {
    const b = table.bytes[i]!;
    if (b === 0x2d) hyphen = true;
    else if (b >= 0x80) accent = true;
  }

  switch (charset) {
    case 'alpha':
      return !hyphen && !accent;
    case 'hyphen':
      return hyphen;
    case 'accent':
      return accent;
    default:
      return true;
  }
}

function sortIndices(indices: Uint32Array, table: WordTable, meta: MetaTable, query: Query): void {
  // Alphabetical is the order the indices are already in, because the source
  // list is sorted and the scan walks it forwards. Only reversal costs anything.
  if (query.sort === 'alpha') {
    if (query.descending) indices.reverse();
    return;
  }

  const key = query.sort === 'length' ? table.lengths : meta.added;
  const direction = query.descending ? -1 : 1;

  // Uint32Array.sort takes a comparator and sorts in place, so this never
  // materialises a 378,891-element JavaScript array.
  indices.sort((a, b) => {
    const d = key[a]! - key[b]!;
    // Ties break alphabetically rather than arbitrarily: with 47 distinct
    // lengths, a length sort is almost entirely ties, and an unstable order
    // would reshuffle the list on every keystroke.
    return (d !== 0 ? d * direction : a - b) as number;
  });
}
