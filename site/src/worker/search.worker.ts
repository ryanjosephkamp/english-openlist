/// <reference lib="webworker" />
import { decodeWords, decodeMeta, wordAt, prefixRange, type WordTable, type MetaTable } from '@eol/wordlist/decode';
import { runQuery, type Query } from '@eol/wordlist/query';
import type { Manifest, Request, Response, Row } from './protocol.ts';

let table: WordTable | null = null;
let meta: MetaTable | null = null;
let manifest: Manifest | null = null;
/** The most recent result set, kept here so scrolling never re-runs the query. */
let current: Uint32Array = new Uint32Array(0);

const encoder = new TextEncoder();

function post(message: Response): void {
  (self as unknown as DedicatedWorkerGlobalScope).postMessage(message);
}

/**
 * Fetch an artifact, preferring the pre-compressed sibling.
 *
 * Cloudflare serves `*.br` with `Content-Encoding: br` (see `public/_headers`),
 * so the browser inflates it transparently and the decoded length matches the
 * manifest. If that header is ever missing the body arrives as raw brotli, the
 * length check fails, and this falls back to the plain `.bin` rather than
 * handing the decoder garbage.
 */
/**
 * What actually crossed the wire for `url`.
 *
 * `ArrayBuffer.byteLength` is the wrong number here: the browser inflates a
 * `Content-Encoding: br` response before handing it over, so it reports the
 * decoded size — 3.10 MB for artifacts that transferred as 666 KB. The
 * Resource Timing entry keeps the encoded size, which is the honest figure.
 *
 * It returns 0 when the entry is missing or cross-origin without
 * Timing-Allow-Origin, in which case the caller falls back to what the build
 * measured.
 */
function encodedSize(url: string): number {
  const entries = performance.getEntriesByName(url, 'resource');
  const last = entries[entries.length - 1] as PerformanceResourceTiming | undefined;
  return last?.encodedBodySize ?? 0;
}

async function fetchArtifact(
  baseUrl: string,
  file: { name: string; bytes: number; brotliBytes: number },
): Promise<{ bytes: Uint8Array; transferred: number }> {
  const plain = `${baseUrl}/${file.name}`;
  const compressed = `${plain}.br`;

  try {
    const response = await fetch(compressed);
    if (response.ok) {
      const buffer = await response.arrayBuffer();
      // A correct response decodes to exactly the length the manifest records.
      // Raw brotli — which is what arrives if the Content-Encoding header ever
      // goes missing — does not, so this is also the guard against handing the
      // decoder a compressed stream.
      if (buffer.byteLength === file.bytes) {
        return {
          bytes: new Uint8Array(buffer),
          transferred: encodedSize(compressed) || file.brotliBytes,
        };
      }
    }
  } catch {
    // No sibling deployed, or the request failed. Fall through.
  }

  const response = await fetch(plain);
  if (!response.ok) throw new Error(`${file.name}: HTTP ${response.status}`);
  const buffer = await response.arrayBuffer();
  return { bytes: new Uint8Array(buffer), transferred: encodedSize(plain) || file.bytes };
}

async function init(baseUrl: string): Promise<void> {
  const response = await fetch(`${baseUrl}/manifest.json`);
  if (!response.ok) throw new Error(`manifest.json: HTTP ${response.status}`);
  manifest = (await response.json()) as Manifest;

  const words = manifest.files['words'];
  const metaFile = manifest.files['meta'];
  if (!words || !metaFile) throw new Error('manifest is missing an artifact');

  const [w, m] = await Promise.all([
    fetchArtifact(baseUrl, words),
    fetchArtifact(baseUrl, metaFile),
  ]);

  const started = performance.now();
  table = decodeWords(w.bytes);
  meta = decodeMeta(m.bytes);
  const decodeMillis = performance.now() - started;

  current = new Uint32Array(table.count);
  for (let i = 0; i < table.count; i++) current[i] = i;

  post({
    type: 'ready',
    manifest,
    transferred: w.transferred + m.transferred,
    decodeMillis,
  });
}

function rowAt(index: number): Row {
  return {
    word: wordAt(table!, index),
    index,
    intake: meta!.intake[index]!,
    added: manifest!.dateTable[meta!.added[index]!] ?? '',
    flags: meta!.flags[index]!,
  };
}

function page(offset: number, limit: number): Row[] {
  const rows: Row[] = [];
  const end = Math.min(offset + limit, current.length);
  for (let i = Math.max(0, offset); i < end; i++) rows.push(rowAt(current[i]!));
  return rows;
}

self.onmessage = (event: MessageEvent<Request>): void => {
  const message = event.data;

  if (message.type === 'init') {
    init(message.baseUrl).catch((cause: unknown) => {
      post({ type: 'failed', message: cause instanceof Error ? cause.message : String(cause) });
    });
    return;
  }

  if (!table || !meta) return;

  switch (message.type) {
    case 'query': {
      const result = runQuery(table, meta, message.query as Query);
      current = result.indices;
      post({
        type: 'result',
        id: message.id,
        count: result.indices.length,
        millis: result.millis,
        error: result.error,
        rows: page(0, message.limit),
      });
      return;
    }
    case 'page': {
      post({ type: 'rows', id: message.id, offset: message.offset, rows: page(message.offset, message.limit) });
      return;
    }
    case 'lookup': {
      const needle = encoder.encode(message.word.trim().toLowerCase());
      const [lo, hi] = prefixRange(table, needle);
      // An exact hit is a prefix range of width one whose word is the needle.
      const found = hi > lo && table.lengths[lo] === needle.length ? rowAt(lo) : null;
      post({ type: 'lookup', id: message.id, row: found });
      return;
    }
  }
};
