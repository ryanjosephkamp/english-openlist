/**
 * Binary artifact format for the shipped word list.
 *
 * Words are front-coded: the list is already sorted, so each entry stores only
 * how many leading *bytes* it shares with its predecessor plus the differing
 * suffix. Measured on the real 378,891-word list, that takes 4,438,385 bytes of
 * newline-delimited text to 1,732,852 raw and 520,857 brotli — 8.5× — and it
 * decodes in 11 ms in a single linear pass.
 *
 * The prefix chain is unbounded: it never restarts, and there is no restart
 * index. Ars Magna's equivalent format restarts every 64 words and records the
 * offsets, because it needs to binary-search a prefix *without* decoding the
 * list first. Here the worker decodes once into a flat table whose offsets give
 * O(log n) search directly, so the restart index would never be read. Measured,
 * it cost 45,773 brotli bytes — 8.1% of the artifact — to carry a section
 * nothing loads, so it is not carried.
 *
 * Bytes, not characters. Ars Magna front-codes `charCodeAt` values, which is
 * safe there only because its build normalizes every word to `[a-z]` first.
 * This site shows words as they actually are, and the list contains 190
 * hyphenated entries plus `norteño` and `peléan`, whose UTF-8 encodings are two
 * bytes wide — front-coding characters would corrupt them. The list is sorted
 * identically by codepoint and by UTF-8 byte order (verified against the real
 * file), so byte-wise prefix comparison stays consistent with the sort, which
 * is what prefix search depends on.
 */

export const MAGIC_WORDS = 'EOLWORDS';
export const MAGIC_META = 'EOLMETA1';
export const FORMAT_VERSION = 1;

export const SECTION_WORDS = 1;
/** One byte per word: which intake the word arrived through. */
export const SECTION_INTAKE = 3;
/** Two bytes per word, little-endian: index into the manifest's date table. */
export const SECTION_ADDED = 4;
/** One byte per word of bit flags; see `WordFlag`. */
export const SECTION_FLAGS = 5;

const HEADER_BYTES = 24;
const SECTION_ENTRY_BYTES = 12;

/**
 * Intake codes, in the order the dataset card documents them. A byte per word
 * rather than a string per word: 378,891 bytes raw, 71,578 brotli.
 */
export const INTAKE = {
  twl: 0,
  pipeline: 1,
  synthetic: 2,
  other: 3,
} as const;

export type IntakeName = keyof typeof INTAKE;

export const INTAKE_NAMES = ['twl', 'pipeline', 'synthetic', 'other'] as const satisfies readonly IntakeName[];

export const WordFlag = {
  /** One LLM pass called the word invalid; the dataset kept it. An opinion, not a verdict. */
  LlmSaysInvalid: 1 << 0,
  /** The word also appears in `merged_invalid_words.txt`. */
  AlsoInvalid: 1 << 1,
  /** Contains something outside `a-z` — a hyphen, or an accented letter. */
  NonAlpha: 1 << 2,
} as const;

function align4(n: number): number {
  return (n + 3) & ~3;
}

export type Section = { readonly kind: number; readonly data: Uint8Array };

export function compareBytes(a: Uint8Array, b: Uint8Array): number {
  const limit = Math.min(a.length, b.length);
  for (let i = 0; i < limit; i++) {
    const d = a[i]! - b[i]!;
    if (d !== 0) return d;
  }
  return a.length - b.length;
}

/** Front-code `words` into the WORDS payload. */
export function frontCode(words: readonly Uint8Array[]): Uint8Array {
  // Worst case: every word stores a shared-length byte, its full bytes, and a
  // terminator.
  let upper = 0;
  for (const w of words) upper += w.length + 2;
  const payload = new Uint8Array(upper);

  let out = 0;
  let previous: Uint8Array = new Uint8Array(0);

  for (const word of words) {
    // 255 is the ceiling one length byte can express. The longest word here is
    // 47 bytes, nowhere near it, but the clamp keeps the format honest if a
    // longer entry ever arrives.
    const limit = Math.min(255, previous.length, word.length);
    let shared = 0;
    while (shared < limit && previous[shared] === word[shared]) shared++;

    payload[out++] = shared;
    for (let c = shared; c < word.length; c++) payload[out++] = word[c]!;
    payload[out++] = 0;

    previous = word;
  }

  return payload.subarray(0, out);
}

function magicBytes(magic: string): Uint8Array {
  const out = new Uint8Array(8);
  for (let i = 0; i < 8; i++) out[i] = magic.charCodeAt(i);
  return out;
}

/**
 * Pack sections behind a fixed header and a section table.
 *
 * Layout: 8-byte magic, u16 version, u16 section count, u32 word count, u32
 * total word bytes, 4 reserved, then one `(u32 kind, u32 offset, u32 length)`
 * entry per section, then the payloads, each 4-byte aligned so a `Uint32Array`
 * view over RESTARTS never straddles an alignment boundary.
 *
 * `totalWordBytes` exists so the browser can allocate the decoded word buffer
 * exactly once, at the right size, instead of guessing an upper bound and
 * trimming a multi-megabyte array afterwards.
 */
export function encodeContainer(
  magic: string,
  wordCount: number,
  totalWordBytes: number,
  sections: readonly Section[],
): Uint8Array {
  const tableBytes = sections.length * SECTION_ENTRY_BYTES;
  let cursor = align4(HEADER_BYTES + tableBytes);

  const placed = sections.map((s) => {
    const offset = cursor;
    cursor = align4(cursor + s.data.length);
    return { ...s, offset };
  });

  const out = new Uint8Array(cursor);
  const view = new DataView(out.buffer);

  out.set(magicBytes(magic), 0);
  view.setUint16(8, FORMAT_VERSION, true);
  view.setUint16(10, sections.length, true);
  view.setUint32(12, wordCount, true);
  view.setUint32(16, totalWordBytes, true);

  let entry = HEADER_BYTES;
  for (const s of placed) {
    view.setUint32(entry, s.kind, true);
    view.setUint32(entry + 4, s.offset, true);
    view.setUint32(entry + 8, s.data.length, true);
    entry += SECTION_ENTRY_BYTES;
    out.set(s.data, s.offset);
  }

  return out;
}

export type Container = {
  readonly wordCount: number;
  readonly totalWordBytes: number;
  readonly sections: ReadonlyMap<number, Uint8Array>;
};

export function decodeContainer(bytes: Uint8Array, magic: string): Container {
  if (bytes.length < HEADER_BYTES) throw new Error('artifact is shorter than its header');

  const expected = magicBytes(magic);
  for (let i = 0; i < 8; i++) {
    if (bytes[i] !== expected[i]) throw new Error(`bad magic: expected ${magic}`);
  }

  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const version = view.getUint16(8, true);
  if (version !== FORMAT_VERSION) {
    throw new Error(`format version ${version}, expected ${FORMAT_VERSION}`);
  }

  const sectionCount = view.getUint16(10, true);
  const wordCount = view.getUint32(12, true);
  const totalWordBytes = view.getUint32(16, true);

  const sections = new Map<number, Uint8Array>();
  let entry = HEADER_BYTES;
  for (let i = 0; i < sectionCount; i++) {
    const kind = view.getUint32(entry, true);
    const offset = view.getUint32(entry + 4, true);
    const length = view.getUint32(entry + 8, true);
    if (offset + length > bytes.length) throw new Error(`section ${kind} runs past the buffer`);
    sections.set(kind, bytes.subarray(offset, offset + length));
    entry += SECTION_ENTRY_BYTES;
  }

  return { wordCount, totalWordBytes, sections };
}

/**
 * Build the shipped word artifact.
 *
 * Asserts sortedness and uniqueness rather than sorting. The source file is
 * already sorted, and a list that has quietly stopped being sorted is a dataset
 * change worth failing a build over, not something to paper over — prefix
 * search would silently return wrong answers.
 */
export function encodeWords(words: readonly Uint8Array[]): Uint8Array {
  const decoder = new TextDecoder();
  let totalWordBytes = 0;
  for (let i = 0; i < words.length; i++) {
    totalWordBytes += words[i]!.length;
    if (i > 0 && compareBytes(words[i - 1]!, words[i]!) >= 0) {
      throw new Error(
        `word list is not sorted and unique at index ${i}: ` +
          `"${decoder.decode(words[i - 1]!)}" then "${decoder.decode(words[i]!)}"`,
      );
    }
  }

  return encodeContainer(MAGIC_WORDS, words.length, totalWordBytes, [
    { kind: SECTION_WORDS, data: frontCode(words) },
  ]);
}

/**
 * Build the columnar metadata artifact.
 *
 * Every column is aligned to the word index, so the browser reads word `i`'s
 * intake at `intake[i]` with no lookup structure at all. Measured against the
 * alternative of a JSON array of `{word, source, date}` objects: 1,115,639
 * bytes brotli for the JSON against ~148 KB for these three columns, because
 * JSON re-encodes the word in every record and the word list is already being
 * shipped separately.
 */
export function encodeMeta(
  wordCount: number,
  intake: Uint8Array,
  added: Uint16Array,
  flags: Uint8Array,
): Uint8Array {
  if (intake.length !== wordCount) throw new Error(`intake length ${intake.length} != ${wordCount}`);
  if (added.length !== wordCount) throw new Error(`added length ${added.length} != ${wordCount}`);
  if (flags.length !== wordCount) throw new Error(`flags length ${flags.length} != ${wordCount}`);

  return encodeContainer(MAGIC_META, wordCount, 0, [
    { kind: SECTION_INTAKE, data: intake },
    {
      kind: SECTION_ADDED,
      data: new Uint8Array(added.buffer, added.byteOffset, added.byteLength),
    },
    { kind: SECTION_FLAGS, data: flags },
  ]);
}
