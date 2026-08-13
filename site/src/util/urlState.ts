import {
  DEFAULT_QUERY,
  type Query,
  type MatchMode,
  type SortKey,
  type Charset,
} from '@eol/wordlist/query';
import { INTAKE_NAMES, type IntakeName } from '@eol/wordlist/format';

/**
 * The query lives in the URL, so a search is a link.
 *
 * Only values that differ from the default are written. A bare `/` is the
 * unfiltered list, and a shared link carries exactly the query that produced
 * what the sender was looking at — no more.
 */
const KEYS = {
  text: 'q',
  mode: 'm',
  minLength: 'min',
  maxLength: 'max',
  intakes: 'i',
  letters: 'l',
  charset: 'ch',
  sort: 's',
  descending: 'd',
  includeContested: 'c',
} as const;

const MODES: readonly MatchMode[] = ['prefix', 'contains', 'suffix', 'pattern', 'regex'];
const SORTS: readonly SortKey[] = ['alpha', 'length', 'added'];
const CHARSETS: readonly Charset[] = ['any', 'alpha', 'hyphen', 'accent'];

export function queryToParams(query: Query): URLSearchParams {
  const params = new URLSearchParams();

  if (query.text) params.set(KEYS.text, query.text);
  if (query.mode !== DEFAULT_QUERY.mode) params.set(KEYS.mode, query.mode);
  if (query.minLength !== DEFAULT_QUERY.minLength) params.set(KEYS.minLength, String(query.minLength));
  if (query.maxLength !== DEFAULT_QUERY.maxLength) params.set(KEYS.maxLength, String(query.maxLength));
  if (query.intakes.length > 0) params.set(KEYS.intakes, query.intakes.join(','));
  if (query.letters.length > 0) params.set(KEYS.letters, query.letters.join(','));
  if (query.charset !== DEFAULT_QUERY.charset) params.set(KEYS.charset, query.charset);
  if (query.sort !== DEFAULT_QUERY.sort) params.set(KEYS.sort, query.sort);
  if (query.descending) params.set(KEYS.descending, '1');
  if (!query.includeContested) params.set(KEYS.includeContested, '0');

  return params;
}

export function paramsToQuery(params: URLSearchParams): Query {
  const mode = params.get(KEYS.mode);
  const sort = params.get(KEYS.sort);
  const charset = params.get(KEYS.charset);

  return {
    text: params.get(KEYS.text) ?? DEFAULT_QUERY.text,
    mode: MODES.includes(mode as MatchMode) ? (mode as MatchMode) : DEFAULT_QUERY.mode,
    minLength: clamp(params.get(KEYS.minLength), DEFAULT_QUERY.minLength),
    maxLength: clamp(params.get(KEYS.maxLength), DEFAULT_QUERY.maxLength),
    intakes: parseIntakes(params.get(KEYS.intakes)),
    letters: parseLetters(params.get(KEYS.letters)),
    charset: CHARSETS.includes(charset as Charset) ? (charset as Charset) : DEFAULT_QUERY.charset,
    sort: SORTS.includes(sort as SortKey) ? (sort as SortKey) : DEFAULT_QUERY.sort,
    descending: params.get(KEYS.descending) === '1',
    includeContested: params.get(KEYS.includeContested) !== '0',
  };
}

function clamp(raw: string | null, fallback: number): number {
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1 || value > 47) return fallback;
  return value;
}

function parseIntakes(raw: string | null): IntakeName[] {
  if (!raw) return [];
  const wanted = new Set(raw.split(','));
  return INTAKE_NAMES.filter((name) => wanted.has(name));
}

function parseLetters(raw: string | null): string[] {
  if (!raw) return [];
  return raw.split(',').filter((letter) => /^[a-z]$/.test(letter));
}

/**
 * Serialize to a path plus search string.
 *
 * `URLSearchParams` encodes a space as `+`, which is correct for form bodies
 * and ugly in a shared link. `%20` reads better and every parser accepts it.
 */
export function queryToUrl(path: string, query: Query): string {
  const params = queryToParams(query).toString().replace(/\+/g, '%20');
  return params ? `${path}?${params}` : path;
}
