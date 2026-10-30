import { DEFAULT_QUERY, type Query, type MatchMode, type SortKey } from '@eol/wordlist/query';
import { DECIDED_NAMES, type DecidedName } from '@eol/wordlist/format';

/**
 * The query lives in the URL, so a search is a link.
 *
 * Only values that differ from the default are written. A bare `/` is the
 * unfiltered list, and a shared link carries exactly the query that produced
 * what the sender was looking at, no more.
 */
const KEYS = {
  text: 'q',
  mode: 'm',
  minLength: 'min',
  maxLength: 'max',
  decided: 'by',
  letters: 'l',
  sort: 's',
  descending: 'd',
  includeContested: 'c',
} as const;

const MODES: readonly MatchMode[] = ['prefix', 'contains', 'suffix', 'pattern', 'regex'];
const SORTS: readonly SortKey[] = ['alpha', 'length', 'added'];

export function queryToParams(query: Query): URLSearchParams {
  const params = new URLSearchParams();
  if (query.text) params.set(KEYS.text, query.text);
  if (query.mode !== DEFAULT_QUERY.mode) params.set(KEYS.mode, query.mode);
  if (query.minLength !== DEFAULT_QUERY.minLength) params.set(KEYS.minLength, String(query.minLength));
  if (query.maxLength !== DEFAULT_QUERY.maxLength) params.set(KEYS.maxLength, String(query.maxLength));
  if (query.decided.length > 0) params.set(KEYS.decided, query.decided.join(','));
  if (query.letters.length > 0) params.set(KEYS.letters, query.letters.join(','));
  if (query.sort !== DEFAULT_QUERY.sort) params.set(KEYS.sort, query.sort);
  if (query.descending) params.set(KEYS.descending, '1');
  if (!query.includeContested) params.set(KEYS.includeContested, '0');
  return params;
}

export function paramsToQuery(params: URLSearchParams): Query {
  const mode = params.get(KEYS.mode);
  const sort = params.get(KEYS.sort);
  return {
    ...DEFAULT_QUERY,
    text: params.get(KEYS.text) ?? DEFAULT_QUERY.text,
    mode: MODES.includes(mode as MatchMode) ? (mode as MatchMode) : DEFAULT_QUERY.mode,
    minLength: length(params.get(KEYS.minLength), DEFAULT_QUERY.minLength),
    maxLength: length(params.get(KEYS.maxLength), DEFAULT_QUERY.maxLength),
    decided: parseDecided(params.get(KEYS.decided)),
    letters: parseLetters(params.get(KEYS.letters)),
    sort: SORTS.includes(sort as SortKey) ? (sort as SortKey) : DEFAULT_QUERY.sort,
    descending: params.get(KEYS.descending) === '1',
    includeContested: params.get(KEYS.includeContested) !== '0',
  };
}

function length(raw: string | null, fallback: number): number {
  const value = Number(raw);
  if (raw === null || !Number.isInteger(value) || value < 1 || value > 255) return fallback;
  return value;
}

function parseDecided(raw: string | null): DecidedName[] {
  if (!raw) return [];
  const wanted = new Set(raw.split(','));
  return DECIDED_NAMES.filter((name) => wanted.has(name));
}

function parseLetters(raw: string | null): string[] {
  if (!raw) return [];
  return [...new Set(raw.split(','))].filter((letter) => /^[a-z]$/.test(letter)).sort();
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
