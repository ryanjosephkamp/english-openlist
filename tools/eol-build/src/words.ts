import { readFile } from 'node:fs/promises';
import { VALID_WORDS } from './paths.ts';

/**
 * Read the word list as UTF-8 byte slices, in file order.
 *
 * Deliberately not decoded to strings. The file is already sorted by UTF-8 byte
 * order — the encoder asserts it — and everything downstream compares bytes, so
 * decoding 378,891 strings only to re-encode them would be wasted work and
 * would hide the two multi-byte entries behind JavaScript's UTF-16.
 */
export async function loadWords(): Promise<Uint8Array[]> {
  const raw = new Uint8Array(await readFile(VALID_WORDS));
  const words: Uint8Array[] = [];

  let start = 0;
  for (let i = 0; i < raw.length; i++) {
    if (raw[i] !== 0x0a) continue;
    // Tolerate CRLF, which nothing in this pipeline writes but which a manual
    // edit on Windows would introduce silently.
    const end = i > start && raw[i - 1] === 0x0d ? i - 1 : i;
    if (end > start) words.push(raw.subarray(start, end));
    start = i + 1;
  }
  if (start < raw.length) words.push(raw.subarray(start));

  return words;
}

/** Read a plain newline-delimited list into a Set of strings. */
export async function loadWordSet(path: string): Promise<Set<string>> {
  const text = await readFile(path, 'utf8');
  const set = new Set<string>();
  for (const line of text.split('\n')) {
    const word = line.trimEnd();
    if (word) set.add(word);
  }
  return set;
}
