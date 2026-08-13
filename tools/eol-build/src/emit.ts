import { createHash } from 'node:crypto';
import { writeFile, mkdir, readdir, rm } from 'node:fs/promises';
import { resolve } from 'node:path';
import zlib from 'node:zlib';
import { DATA_DIR } from './paths.ts';

export function sha256(data: Uint8Array): string {
  return createHash('sha256').update(data).digest('hex');
}

/**
 * Brotli at quality 11.
 *
 * Build-time, not on-the-fly: the artifact is written once per deploy and read
 * on every first visit, so the slowest setting is the right one. Cloudflare
 * serves the `.br` sibling directly via a `Content-Encoding` header in
 * `_headers` rather than negotiating between the two files.
 */
export function brotli(data: Uint8Array): Buffer {
  return zlib.brotliCompressSync(data, {
    params: {
      [zlib.constants.BROTLI_PARAM_QUALITY]: 11,
      [zlib.constants.BROTLI_PARAM_SIZE_HINT]: data.length,
    },
  });
}

export type Artifact = {
  readonly key: string;
  readonly name: string;
  readonly bytes: number;
  readonly brotliBytes: number;
  readonly sha256: string;
};

/**
 * Write `data` under a content-hashed name, alongside its brotli sibling.
 *
 * The hash in the filename is what lets `_headers` cache these immutably for a
 * year: a rebuilt artifact is a new URL, so a stale copy can never be served.
 * Only `manifest.json` — the pointer to these names — stays short-lived.
 */
export async function emit(key: string, extension: string, data: Uint8Array): Promise<Artifact> {
  const digest = sha256(data);
  const name = `${key}.${digest.slice(0, 12)}.${extension}`;
  const compressed = brotli(data);

  await mkdir(DATA_DIR, { recursive: true });
  await writeFile(resolve(DATA_DIR, name), data);
  await writeFile(resolve(DATA_DIR, `${name}.br`), compressed);

  return { key, name, bytes: data.length, brotliBytes: compressed.length, sha256: digest };
}

/**
 * Delete artifacts from previous builds.
 *
 * Without this the output directory accumulates every word list ever built and
 * the deploy uploads all of them.
 *
 * `alsoKeep` is not optional in practice: anything written into this directory
 * that is not a content-hashed artifact has to be named here or it is deleted
 * moments after being written. That is exactly what happened to `stats.json`
 * the first time, and the failure surfaced only in the browser, as the Shape
 * page fetching JSON and being handed `index.html` by the SPA fallback.
 */
export async function clearStale(
  keep: readonly Artifact[],
  alsoKeep: readonly string[],
): Promise<number> {
  const wanted = new Set<string>(alsoKeep);
  for (const artifact of keep) {
    wanted.add(artifact.name);
    wanted.add(`${artifact.name}.br`);
  }
  wanted.add('manifest.json');

  let removed = 0;
  let entries: string[];
  try {
    entries = await readdir(DATA_DIR);
  } catch {
    return 0;
  }

  for (const entry of entries) {
    if (wanted.has(entry)) continue;
    await rm(resolve(DATA_DIR, entry), { recursive: true, force: true });
    removed++;
  }
  return removed;
}

export const kb = (n: number): string => `${(n / 1024).toFixed(1)} KB`;
