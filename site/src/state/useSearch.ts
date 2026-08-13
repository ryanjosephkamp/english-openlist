import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Query } from '@eol/wordlist/query';
import type { Manifest, Request, Response, Row } from '../worker/protocol.ts';

/** Rows fetched per request. Comfortably more than a screen, so scrolling rarely waits. */
const PAGE = 240;
/**
 * Typing pause before a query runs.
 *
 * The heaviest scan measured 52 ms, so a keystroke is never the thing that
 * blocks; this exists to stop five queries running while someone types five
 * letters, not to hide latency.
 */
const DEBOUNCE_MS = 140;

export type SearchStatus = 'loading' | 'ready' | 'failed';

export type Search = {
  readonly status: SearchStatus;
  readonly failure: string | null;
  readonly manifest: Manifest | null;
  readonly transferred: number;
  readonly decodeMillis: number;
  readonly count: number;
  readonly millis: number;
  /** Set when the query itself was rejected — an unparseable regular expression. */
  readonly error: string | null;
  readonly searching: boolean;
  readonly rowAt: (index: number) => Row | undefined;
  readonly lookup: (word: string) => Promise<Row | null>;
};

export function useSearch(query: Query): Search {
  const workerRef = useRef<Worker | null>(null);
  const [status, setStatus] = useState<SearchStatus>('loading');
  const [failure, setFailure] = useState<string | null>(null);
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [transferred, setTransferred] = useState(0);
  const [decodeMillis, setDecodeMillis] = useState(0);
  const [count, setCount] = useState(0);
  const [millis, setMillis] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);

  // Rows arrive a page at a time and are read during render, so they live in a
  // ref with a version counter rather than in state: replacing a 240-entry Map
  // on every scroll would rerender the whole list for rows already on screen.
  const rows = useRef(new Map<number, Row>());
  const requested = useRef(new Set<number>());
  const [, bump] = useState(0);

  const nextId = useRef(1);
  const queryId = useRef(0);
  const pending = useRef(new Map<number, (row: Row | null) => void>());

  useEffect(() => {
    const worker = new Worker(new URL('../worker/search.worker.ts', import.meta.url), {
      type: 'module',
    });
    workerRef.current = worker;

    worker.onmessage = (event: MessageEvent<Response>) => {
      const message = event.data;

      switch (message.type) {
        case 'ready':
          setManifest(message.manifest);
          setTransferred(message.transferred);
          setDecodeMillis(message.decodeMillis);
          setCount(message.manifest.wordCount);
          setStatus('ready');
          return;

        case 'failed':
          setFailure(message.message);
          setStatus('failed');
          return;

        case 'result': {
          // A slow query that finished after a newer one started must not
          // overwrite the newer result.
          if (message.id !== queryId.current) return;
          rows.current = new Map();
          requested.current = new Set([0]);
          message.rows.forEach((row, i) => rows.current.set(i, row));
          setCount(message.count);
          setMillis(message.millis);
          setError(message.error);
          setSearching(false);
          bump((v) => v + 1);
          return;
        }

        case 'rows': {
          message.rows.forEach((row, i) => rows.current.set(message.offset + i, row));
          bump((v) => v + 1);
          return;
        }

        case 'lookup': {
          pending.current.get(message.id)?.(message.row);
          pending.current.delete(message.id);
          return;
        }
      }
    };

    const send = (request: Request) => worker.postMessage(request);
    send({ type: 'init', baseUrl: `${import.meta.env.BASE_URL}data`.replace(/\/{2,}/g, '/') });

    return () => worker.terminate();
  }, []);

  useEffect(() => {
    if (status !== 'ready') return;

    setSearching(true);
    const id = nextId.current++;
    queryId.current = id;

    const timer = setTimeout(() => {
      workerRef.current?.postMessage({ type: 'query', id, query, limit: PAGE } satisfies Request);
    }, DEBOUNCE_MS);

    return () => clearTimeout(timer);
  }, [status, query]);

  const rowAt = useCallback((index: number): Row | undefined => {
    const row = rows.current.get(index);
    if (row) return row;

    const pageStart = Math.floor(index / PAGE) * PAGE;
    if (!requested.current.has(pageStart)) {
      requested.current.add(pageStart);
      workerRef.current?.postMessage({
        type: 'page',
        id: nextId.current++,
        offset: pageStart,
        limit: PAGE,
      } satisfies Request);
    }
    return undefined;
  }, []);

  const lookup = useCallback((word: string): Promise<Row | null> => {
    const worker = workerRef.current;
    if (!worker) return Promise.resolve(null);
    const id = nextId.current++;
    return new Promise((resolve) => {
      pending.current.set(id, resolve);
      worker.postMessage({ type: 'lookup', id, word } satisfies Request);
    });
  }, []);

  return useMemo(
    () => ({
      status,
      failure,
      manifest,
      transferred,
      decodeMillis,
      count,
      millis,
      error,
      searching,
      rowAt,
      lookup,
    }),
    [status, failure, manifest, transferred, decodeMillis, count, millis, error, searching, rowAt, lookup],
  );
}
