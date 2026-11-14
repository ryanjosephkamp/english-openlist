import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { Attested, WordFlag } from '@eol/wordlist/format';
import { DOWNLOADS_DIR } from './paths.ts';

/**
 * Prebuilt filtered word lists.
 *
 * The filter everyone wants first is "without the synthetic entries", and doing
 * it yourself means downloading the whole metadata file and reading every
 * record. These are the same answers as plain text, rebuilt from the dataset on
 * every deploy, so nobody has to.
 *
 * Each list is cut by a property of the word, or by the synthetic engine flag,
 * and never by any other intake.
 */
export type Download = {
  readonly file: string;
  readonly label: string;
  readonly note: string;
  readonly words: number;
  readonly bytes: number;
};

type Word = { readonly length: number; readonly attested: number; readonly flags: number };

const BUILDS: readonly { file: string; label: string; note: string; keep: (w: Word) => boolean }[] = [
  {
    file: 'without-synthetic.txt',
    label: 'Without the synthetic engine',
    note: 'Every entry except those the synthetic engine made.',
    keep: (w) => (w.flags & WordFlag.Engine) === 0,
  },
  {
    file: 'listed-by-an-open-source.txt',
    label: 'Listed by an open source',
    note: 'Every entry that at least 1 of the open sources lists: Wiktionary, WordNet, SCOWL, the LibreOffice dictionaries, ENABLE, or wordfreq.',
    keep: (w) => (w.attested & Attested.Sources) !== 0,
  },
  {
    file: 'lengths-2-to-45.txt',
    label: 'Lengths 2 to 45',
    note: "The list's length bounds before August 16, 2026. The full list breaks both on purpose: it holds 1-letter words and words longer than 45 letters.",
    keep: (w) => w.length >= 2 && w.length <= 45,
  },
];

export async function writeDownloads(
  words: readonly Uint8Array[],
  attested: Uint8Array,
  flags: Uint8Array,
): Promise<Download[]> {
  await mkdir(DOWNLOADS_DIR, { recursive: true });
  const decoder = new TextDecoder();
  const out: Download[] = [];

  for (const build of BUILDS) {
    const lines: string[] = [];
    for (let i = 0; i < words.length; i++) {
      if (build.keep({ length: words[i]!.length, attested: attested[i]!, flags: flags[i]! })) {
        lines.push(decoder.decode(words[i]!));
      }
    }
    const text = `${lines.join('\n')}\n`;
    await writeFile(resolve(DOWNLOADS_DIR, build.file), text, 'utf8');
    out.push({ file: build.file, label: build.label, note: build.note, words: lines.length, bytes: Buffer.byteLength(text) });
  }

  return out;
}
