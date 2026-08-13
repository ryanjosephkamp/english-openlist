import type { Query } from '@eol/wordlist/query';

/**
 * A single result row, in the shape the list renders.
 *
 * The worker keeps the current result set to itself and hands over only the
 * rows on screen. Transferring all 378,891 matching indices on every keystroke
 * would be 1.5 MB per press for a list that shows forty of them; a page is
 * roughly 3 KB.
 */
export type Row = {
  readonly word: string;
  readonly index: number;
  readonly intake: number;
  /** `YYYY-MM-DD`, or empty when the record carries no date. */
  readonly added: string;
  readonly flags: number;
};

export type Manifest = {
  readonly builtAt: string;
  readonly wordCount: number;
  readonly dateTable: readonly string[];
  readonly intakeCounts: Readonly<Record<string, number>>;
  readonly statusInvalid: number;
  readonly alsoInvalid: number;
  readonly alsoInvalidWords: readonly string[];
  readonly nonAlpha: number;
  readonly addedSingly: number;
  readonly bulkDates: readonly { date: string; count: number }[];
  /** String tables the provenance shards index into, rather than repeating. */
  readonly provenance: {
    readonly shards: number;
    readonly sources: readonly string[];
    readonly manualSources: readonly string[];
    readonly llms: readonly string[];
    readonly categories: readonly string[];
    readonly statuses: readonly string[];
    readonly words: number;
    readonly withDefinition: number;
  };
  readonly files: Readonly<Record<string, { name: string; bytes: number; brotliBytes: number }>>;
};

export type Request =
  | { readonly type: 'init'; readonly baseUrl: string }
  | { readonly type: 'query'; readonly id: number; readonly query: Query; readonly limit: number }
  | { readonly type: 'page'; readonly id: number; readonly offset: number; readonly limit: number }
  | { readonly type: 'lookup'; readonly id: number; readonly word: string };

export type Response =
  | {
      readonly type: 'ready';
      readonly manifest: Manifest;
      /** Bytes actually transferred, so the interface can state the real cost. */
      readonly transferred: number;
      readonly decodeMillis: number;
    }
  | { readonly type: 'failed'; readonly message: string }
  | {
      readonly type: 'result';
      readonly id: number;
      readonly count: number;
      readonly millis: number;
      readonly error: string | null;
      readonly rows: readonly Row[];
    }
  | { readonly type: 'rows'; readonly id: number; readonly offset: number; readonly rows: readonly Row[] }
  | { readonly type: 'lookup'; readonly id: number; readonly row: Row | null };
