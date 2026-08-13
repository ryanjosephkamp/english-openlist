import { createWriteStream } from 'node:fs';
import { mkdir, rename, stat, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { Readable } from 'node:stream';
import { pipeline } from 'node:stream/promises';
import { CACHE_DIR, HF_BASE, HF_REPO } from './paths.ts';

/**
 * Download the dataset files the build reads.
 *
 * Against `main`, not a pinned revision. Ars Magna pins deliberately — a silent
 * dictionary change there silently changes every result it produces. This site
 * *is* English OpenList's own surface, so it should show what the dataset says
 * today; the daily pipeline pushes at about 00:26 UTC and this rebuilds behind
 * it.
 *
 * The 291 MB metadata file only changes on days a word is promoted, so the
 * revision is recorded and re-downloads are skipped when it has not moved. On
 * CI that pairs with actions/cache keyed on the same revision.
 */
const FILES = [
  { path: 'data/merged_valid_words.txt', local: 'merged_valid_words.txt' },
  { path: 'data/merged_valid_dict.json', local: 'merged_valid_dict.json' },
  { path: 'data/merged_invalid_words.txt', local: 'merged_invalid_words.txt' },
] as const;

const STAMP = resolve(CACHE_DIR, '.revision');

async function currentRevision(): Promise<string> {
  const response = await fetch(`https://huggingface.co/api/datasets/${HF_REPO}`);
  if (!response.ok) throw new Error(`dataset info: HTTP ${response.status}`);
  const info = (await response.json()) as { sha?: string };
  if (!info.sha) throw new Error('dataset info carried no revision');
  return info.sha;
}

async function sizeOf(path: string): Promise<number> {
  try {
    return (await stat(path)).size;
  } catch {
    return -1;
  }
}

async function download(remote: string, target: string): Promise<number> {
  const response = await fetch(`${HF_BASE}/${remote}`, { redirect: 'follow' });
  if (!response.ok) throw new Error(`${remote}: HTTP ${response.status}`);
  if (!response.body) throw new Error(`${remote}: no response body`);

  // Written to `.part` and renamed, so an interrupted run cannot leave a
  // truncated file that the next build reads as complete.
  const part = `${target}.part`;
  await pipeline(Readable.fromWeb(response.body as never), createWriteStream(part));
  await rename(part, target);
  return await sizeOf(target);
}

const kb = (n: number) => `${(n / 1024 / 1024).toFixed(1)} MB`;

await mkdir(CACHE_DIR, { recursive: true });

const revision = await currentRevision();
const cached = await readFile(STAMP, 'utf8').catch(() => '');
const fresh = cached.trim() === revision;

console.log(`dataset revision ${revision.slice(0, 12)}${fresh ? ' (cache is current)' : ''}`);

let downloaded = 0;
for (const file of FILES) {
  const target = resolve(CACHE_DIR, file.local);
  const existing = await sizeOf(target);

  if (fresh && existing > 0) {
    console.log(`  have  ${file.local.padEnd(26)} ${kb(existing).padStart(9)}`);
    continue;
  }

  const size = await download(file.path, target);
  downloaded += size;
  console.log(`  got   ${file.local.padEnd(26)} ${kb(size).padStart(9)}`);
}

await writeFile(STAMP, `${revision}\n`);

console.log(
  downloaded > 0 ? `\ndownloaded ${kb(downloaded)}\n` : '\nnothing to download\n',
);
