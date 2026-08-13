import {
  MAGIC_WORDS,
  MAGIC_META,
  SECTION_WORDS,
  SECTION_INTAKE,
  SECTION_ADDED,
  SECTION_FLAGS,
  decodeContainer,
} from './format.ts';

/**
 * The decoded word list, held flat.
 *
 * Not a `string[]`. 378,891 JavaScript strings cost roughly 40 MB of heap and
 * make every filter pass chase pointers; the same words as one contiguous
 * `Uint8Array` plus an offset table are 4,059,492 + 1,515,568 bytes and scan at
 * memory speed. Strings are materialised only for the rows actually on screen.
 */
export type WordTable = {
  readonly count: number;
  /** Every word's UTF-8 bytes, concatenated, with no separators. */
  readonly bytes: Uint8Array;
  /** `count + 1` entries: word `i` is `bytes[offsets[i] .. offsets[i + 1]]`. */
  readonly offsets: Uint32Array;
  /** Byte length of each word. Precomputed because length is a primary filter. */
  readonly lengths: Uint8Array;
};

export function decodeWords(bytes: Uint8Array): WordTable {
  const container = decodeContainer(bytes, MAGIC_WORDS);
  const payload = container.sections.get(SECTION_WORDS);
  if (!payload) throw new Error('word artifact has no WORDS section');

  const count = container.wordCount;
  const flat = new Uint8Array(container.totalWordBytes);
  const offsets = new Uint32Array(count + 1);
  const lengths = new Uint8Array(count);

  let out = 0;
  let at = 0;
  let previousStart = 0;

  for (let i = 0; i < count; i++) {
    const shared = payload[at++]!;
    const start = out;

    // The shared prefix is copied from the previous word, which is already
    // sitting in `flat`. The regions never overlap: `out` is always at or past
    // the end of the previous word, and `shared` never exceeds its length.
    for (let k = 0; k < shared; k++) flat[out++] = flat[previousStart + k]!;
    while (payload[at] !== 0) flat[out++] = payload[at++]!;
    at++; // terminator

    offsets[i] = start;
    lengths[i] = out - start;
    previousStart = start;
  }

  offsets[count] = out;

  if (out !== container.totalWordBytes) {
    throw new Error(`decoded ${out} bytes, header declared ${container.totalWordBytes}`);
  }

  return { count, bytes: flat, offsets, lengths };
}

export type MetaTable = {
  readonly intake: Uint8Array;
  readonly added: Uint16Array;
  readonly flags: Uint8Array;
};

export function decodeMeta(bytes: Uint8Array): MetaTable {
  const container = decodeContainer(bytes, MAGIC_META);

  const intake = container.sections.get(SECTION_INTAKE);
  const addedRaw = container.sections.get(SECTION_ADDED);
  const flags = container.sections.get(SECTION_FLAGS);
  if (!intake || !addedRaw || !flags) throw new Error('meta artifact is missing a column');

  // `addedRaw` is a subarray of the fetched buffer, and its byteOffset is
  // 4-aligned by construction, so a Uint16Array view over it is always legal.
  const added = new Uint16Array(addedRaw.buffer, addedRaw.byteOffset, addedRaw.byteLength / 2);

  return { intake, added, flags };
}

const decoder = new TextDecoder();

export function wordAt(table: WordTable, index: number): string {
  return decoder.decode(table.bytes.subarray(table.offsets[index]!, table.offsets[index + 1]!));
}

/** Compare word `index` against a UTF-8 needle, byte-wise. */
export function compareAt(table: WordTable, index: number, needle: Uint8Array): number {
  const start = table.offsets[index]!;
  const length = table.lengths[index]!;
  const limit = Math.min(length, needle.length);
  for (let i = 0; i < limit; i++) {
    const d = table.bytes[start + i]! - needle[i]!;
    if (d !== 0) return d;
  }
  return length - needle.length;
}

/**
 * The half-open index range of words starting with `prefix`.
 *
 * Two binary searches over the sorted list. The list is sorted by UTF-8 byte
 * order, and every word sharing a prefix is contiguous under that ordering, so
 * the range is exact rather than a candidate set needing a second filter.
 */
export function prefixRange(table: WordTable, prefix: Uint8Array): [number, number] {
  if (prefix.length === 0) return [0, table.count];

  const lower = lowerBound(table, prefix);

  // The upper bound is the first word that does not start with `prefix`. Rather
  // than incrementing the last byte — which breaks on 0xFF and on multi-byte
  // UTF-8 — walk forward from `lower` using the prefix test directly.
  let hi = table.count;
  let lo = lower;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (startsWith(table, mid, prefix)) lo = mid + 1;
    else hi = mid;
  }

  return [lower, lo];
}

function lowerBound(table: WordTable, needle: Uint8Array): number {
  let lo = 0;
  let hi = table.count;
  while (lo < hi) {
    const mid = (lo + hi) >>> 1;
    if (compareAt(table, mid, needle) < 0) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

export function startsWith(table: WordTable, index: number, prefix: Uint8Array): boolean {
  if (table.lengths[index]! < prefix.length) return false;
  const start = table.offsets[index]!;
  for (let i = 0; i < prefix.length; i++) {
    if (table.bytes[start + i] !== prefix[i]) return false;
  }
  return true;
}

/** Does word `index` contain `needle` anywhere? Plain byte scan. */
export function includesAt(table: WordTable, index: number, needle: Uint8Array): boolean {
  const start = table.offsets[index]!;
  const length = table.lengths[index]!;
  const last = length - needle.length;
  if (last < 0) return false;

  outer: for (let i = 0; i <= last; i++) {
    for (let k = 0; k < needle.length; k++) {
      if (table.bytes[start + i + k] !== needle[k]) continue outer;
    }
    return true;
  }
  return false;
}

export function endsWithAt(table: WordTable, index: number, needle: Uint8Array): boolean {
  const length = table.lengths[index]!;
  if (length < needle.length) return false;
  const start = table.offsets[index]! + length - needle.length;
  for (let i = 0; i < needle.length; i++) {
    if (table.bytes[start + i] !== needle[i]) return false;
  }
  return true;
}
