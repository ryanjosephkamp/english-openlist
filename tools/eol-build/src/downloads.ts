import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { INTAKE } from '@eol/wordlist/format';
import { DOWNLOADS_DIR } from './paths.ts';

/**
 * Prebuilt filtered word lists.
 *
 * The filter everyone wants first is "without the synthetic entries", and doing
 * it yourself means downloading 291 MB of metadata and holding ~2 GB while
 * `json.load` runs. These are the same answers as plain text, rebuilt from the
 * live dataset on every deploy, so nobody has to.
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
    file: 'human-attested.txt',
    label: 'Human-attested only',
    note: 'Everything except the algorithmically constructed entries.',
    keep: (intake: number) => intake !== INTAKE.synthetic,
  },
  {
    file: 'tournament.txt',
    label: 'Tournament word list only',
    note: 'The tournament Scrabble intake on its own — the most conservative slice.',
    keep: (intake: number) => intake === INTAKE.twl,
  },
  {
    // Was 'Strictly a–z', which dropped 188 hyphenated and 2 accented entries.
    // Those were deleted from the list itself on 2026-08-16, so that slice became
    // a copy of the full list. This replaces it with the one people actually lost
    // in the same change: the main list is no longer Scrabble-legal, because it
    // now carries one-letter words and words past 45 characters.
    file: 'scrabble-legal.txt',
    label: 'Scrabble-legal subset',
    note: 'Length 2–45, the tournament-dictionary bounds. The full list deliberately breaks both — see the rule change of 16 August 2026.',
    keep: (_intake: number, _nonAlpha: boolean, length: number) => length >= 2 && length <= 45,
  },
] as const;

export async function writeDownloads(
  words: readonly Uint8Array[],
  intake: Uint8Array,
  nonAlpha: readonly boolean[],
): Promise<Download[]> {
  await mkdir(DOWNLOADS_DIR, { recursive: true });
  const decoder = new TextDecoder();
  const out: Download[] = [];

  for (const build of BUILDS) {
    const lines: string[] = [];
    for (let i = 0; i < words.length; i++) {
      if (build.keep(intake[i]!, nonAlpha[i]!, words[i]!.length)) {
        lines.push(decoder.decode(words[i]!));
      }
    }
    const text = `${lines.join('\n')}\n`;
    await writeFile(resolve(DOWNLOADS_DIR, build.file), text, 'utf8');
    out.push({
      file: build.file,
      label: build.label,
      note: build.note,
      words: lines.length,
      bytes: Buffer.byteLength(text),
    });
  }

  return out;
}
