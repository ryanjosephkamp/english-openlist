import { useEffect, useState } from 'react';

/**
 * One word's provenance record, as stored in a shard.
 *
 * Single-letter keys, and every repeated string is an index into a table on the
 * manifest. See tools/eol-build/src/provenance.ts — the two must agree.
 */
export type Provenance = {
  a?: number[];
  u?: number[];
  d?: string;
  m?: [number, number, string, number];
  c?: number;
  s?: number;
  p?: number;
  g?: number;
  def?: string;
  pos?: string;
  pron?: string;
};

/** Must match tools/eol-build/src/provenance.ts exactly or lookups miss. */
function fnv1a(word: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < word.length; i++) {
    hash ^= word.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash >>> 0;
}

/**
 * Shards already fetched, kept for the session.
 *
 * A shard is ~6.4 KB gzipped and holds roughly 740 words, so following a few
 * links inside one is free after the first. Not an LRU: at 38 KB decoded, even
 * a hundred of them is less memory than the word list itself.
 */
const cache = new Map<number, Promise<Record<string, Provenance>>>();

function loadShard(shard: number): Promise<Record<string, Provenance>> {
  let pending = cache.get(shard);
  if (!pending) {
    const url = `${import.meta.env.BASE_URL}data/prov/${shard}.json`.replace(/\/{2,}/g, '/');
    pending = fetch(url).then((response) => {
      if (!response.ok) throw new Error(`shard ${shard}: HTTP ${response.status}`);
      return response.json() as Promise<Record<string, Provenance>>;
    });
    cache.set(shard, pending);
  }
  return pending;
}

export type ProvenanceState =
  | { status: 'loading' }
  | { status: 'ready'; provenance: Provenance | null }
  | { status: 'failed'; message: string };

export function useProvenance(word: string | null, shards: number | undefined): ProvenanceState {
  const [state, setState] = useState<ProvenanceState>({ status: 'loading' });

  useEffect(() => {
    if (!word || !shards) return;
    let live = true;
    setState({ status: 'loading' });

    loadShard(fnv1a(word) % shards)
      .then((records) => {
        if (live) setState({ status: 'ready', provenance: records[word] ?? null });
      })
      .catch((cause: unknown) => {
        if (live) {
          setState({
            status: 'failed',
            message: cause instanceof Error ? cause.message : String(cause),
          });
        }
      });

    return () => {
      live = false;
    };
  }, [word, shards]);

  return state;
}
