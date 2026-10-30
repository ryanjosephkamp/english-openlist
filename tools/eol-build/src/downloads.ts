import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { DECIDED } from '@eol/wordlist/format';
import { DOWNLOADS_DIR } from './paths.ts';

/**
 * Prebuilt filtered word lists.
 *
 * The filter everyone wants first is "without the synthetic entries", and doing
 * it yourself means downloading 291 MB of metadata and holding ~2 GB while
 * `json.load` runs. These are the same answers as plain text, rebuilt from the
 * dataset on every deploy, so nobody has to.
 *
 * No list here is cut by a channel the public files withhold: a list of the
 * tournament word list's entries alone would publish that list's selection.
 */
export type Download = {
  readonly file: string;
  readonly label: string;
  readonly note: string;
  readonly words: number;
  readonly bytes: number;
};

const BUILDS = [
  {
    file: 'without-synthetic.txt',
    label: 'Without the synthetic engine',
    note: 'Every entry except those the synthetic engine made.',
    keep: (decided: number) => decided !== DECIDED.engine,
  },
  {
    file: 'lengths-2-to-45.txt',
    label: 'Lengths 2 to 45',
    note: 'The bounds of tournament word lists. The full list breaks both on purpose: it holds 1-letter words and words longer than 45 letters.',
    keep: (_decided: number, length: number) => length >= 2 && length <= 45,
  },
] as const;

export async function writeDownloads(words: readonly Uint8Array[], decided: Uint8Array): Promise<Download[]> {
  await mkdir(DOWNLOADS_DIR, { recursive: true });
  const decoder = new TextDecoder();
  const out: Download[] = [];

  for (const build of BUILDS) {
    const lines: string[] = [];
    for (let i = 0; i < words.length; i++) {
      if (build.keep(decided[i]!, words[i]!.length)) lines.push(decoder.decode(words[i]!));
    }
    const text = `${lines.join('\n')}\n`;
    await writeFile(resolve(DOWNLOADS_DIR, build.file), text, 'utf8');
    out.push({ file: build.file, label: build.label, note: build.note, words: lines.length, bytes: Buffer.byteLength(text) });
  }

  return out;
}
