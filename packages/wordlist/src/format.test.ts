import { describe, expect, it } from 'vitest';
import { encodeWords, encodeMeta, frontCode, compareBytes, WordFlag, INTAKE } from './format.ts';
import { decodeWords, decodeMeta, wordAt, prefixRange, includesAt, endsWithAt } from './decode.ts';

const encoder = new TextEncoder();
const bytes = (word: string) => encoder.encode(word);

/**
 * A list shaped like the real one: sorted by UTF-8 byte order, with a hyphenated
 * entry sorting before the letters and two multi-byte words sorting after them.
 * Those three are where a character-wise front-coder would break.
 */
const SAMPLE = [
  'ad-lib',
  'a',
  'aa',
  'aah',
  'aahed',
  'zyzzyva',
  'zzz',
  'norteño',
  'peléan',
]
  .map(bytes)
  .sort(compareBytes);

describe('front coding', () => {
  it('round-trips the sample, hyphens and accents included', () => {
    const table = decodeWords(encodeWords(SAMPLE));
    expect(table.count).toBe(SAMPLE.length);

    const decoded = Array.from({ length: table.count }, (_, i) => wordAt(table, i));
    expect(decoded).toEqual(SAMPLE.map((w) => new TextDecoder().decode(w)));
  });

  it('records byte lengths, not character lengths', () => {
    const table = decodeWords(encodeWords(SAMPLE));
    const index = Array.from({ length: table.count }, (_, i) => wordAt(table, i)).indexOf('norteño');

    // 7 characters, 8 bytes: ñ is two. The interface shows the character count,
    // so anything reading `lengths` for display has to know this.
    expect(table.lengths[index]).toBe(8);
    expect(wordAt(table, index)).toHaveLength(7);
  });

  it('shares prefixes rather than repeating them', () => {
    const payload = frontCode(SAMPLE);
    const flat = SAMPLE.reduce((sum, w) => sum + w.length, 0);
    expect(payload.length).toBeLessThan(flat + SAMPLE.length * 2);
  });

  it('refuses an unsorted list rather than encoding one', () => {
    expect(() => encodeWords([bytes('b'), bytes('a')])).toThrow(/not sorted/);
  });

  it('refuses a duplicate', () => {
    expect(() => encodeWords([bytes('a'), bytes('a')])).toThrow(/not sorted/);
  });

  it('handles an empty list', () => {
    const table = decodeWords(encodeWords([]));
    expect(table.count).toBe(0);
  });
});

describe('prefix search', () => {
  const table = decodeWords(encodeWords(SAMPLE));

  it('finds a contiguous run', () => {
    const [lo, hi] = prefixRange(table, bytes('aa'));
    const found = [];
    for (let i = lo; i < hi; i++) found.push(wordAt(table, i));
    expect(found).toEqual(['aa', 'aah', 'aahed']);
  });

  it('returns the whole list for an empty prefix', () => {
    expect(prefixRange(table, bytes(''))).toEqual([0, SAMPLE.length]);
  });

  it('returns an empty range for a miss', () => {
    const [lo, hi] = prefixRange(table, bytes('q'));
    expect(hi - lo).toBe(0);
  });

  it('matches a multi-byte prefix without splitting the character', () => {
    const [lo, hi] = prefixRange(table, bytes('norte'));
    expect(hi - lo).toBe(1);
    expect(wordAt(table, lo)).toBe('norteño');
  });

  it('does not treat the last word as unbounded', () => {
    const [lo, hi] = prefixRange(table, bytes('zzz'));
    expect(hi - lo).toBe(1);
    expect(wordAt(table, lo)).toBe('zzz');
  });
});

describe('substring and suffix', () => {
  const table = decodeWords(encodeWords(SAMPLE));
  const indexOf = (word: string) =>
    Array.from({ length: table.count }, (_, i) => wordAt(table, i)).indexOf(word);

  it('finds an interior match', () => {
    expect(includesAt(table, indexOf('zyzzyva'), bytes('zzy'))).toBe(true);
    expect(includesAt(table, indexOf('zyzzyva'), bytes('qqq'))).toBe(false);
  });

  it('does not match a needle longer than the word', () => {
    expect(includesAt(table, indexOf('a'), bytes('aa'))).toBe(false);
  });

  it('matches a suffix only at the end', () => {
    expect(endsWithAt(table, indexOf('aahed'), bytes('hed'))).toBe(true);
    expect(endsWithAt(table, indexOf('aahed'), bytes('aah'))).toBe(false);
  });
});

describe('columnar metadata', () => {
  it('round-trips every column', () => {
    const count = 5;
    const intake = new Uint8Array([INTAKE.twl, INTAKE.pipeline, INTAKE.synthetic, INTAKE.other, INTAKE.twl]);
    const added = new Uint16Array([0, 1, 2, 65535, 7]);
    const flags = new Uint8Array([
      0,
      WordFlag.StatusInvalid,
      WordFlag.AlsoInvalid,
      WordFlag.StatusInvalid | WordFlag.NonAlpha,
      WordFlag.NonAlpha,
    ]);

    const back = decodeMeta(encodeMeta(count, intake, added, flags));
    expect(Array.from(back.intake)).toEqual(Array.from(intake));
    expect(Array.from(back.added)).toEqual(Array.from(added));
    expect(Array.from(back.flags)).toEqual(Array.from(flags));
  });

  it('refuses a column of the wrong length', () => {
    expect(() => encodeMeta(3, new Uint8Array(2), new Uint16Array(3), new Uint8Array(3))).toThrow(
      /intake length/,
    );
  });
});

describe('container', () => {
  it('rejects a buffer with the wrong magic', () => {
    const words = encodeWords(SAMPLE);
    expect(() => decodeMeta(words)).toThrow(/bad magic/);
  });
});
