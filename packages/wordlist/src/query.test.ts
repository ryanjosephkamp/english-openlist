import { describe, expect, it } from 'vitest';
import { encodeWords, encodeMeta, compareBytes, Attested, WordFlag, attesterBit } from './format.ts';
import { decodeWords, decodeMeta, wordAt } from './decode.ts';
import { runQuery, DEFAULT_QUERY, type Query } from './query.ts';

const encoder = new TextEncoder();

const WORDS = ['cat', 'cot', 'cut', 'cart', 'dog', 'dogs', 'zzz', 'ad-lib', 'norteño']
  .map((w) => encoder.encode(w))
  .sort(compareBytes);

const table = decodeWords(encodeWords(WORDS));
const names = Array.from({ length: table.count }, (_, i) => wordAt(table, i));

// Which open sources list each word, and flags, assigned by word so the
// filters have something to bite on.
const LISTED: Readonly<Record<string, number>> = {
  cat: attesterBit('wiktionary') | attesterBit('scowl'),
  cot: attesterBit('wordnet'),
  cut: attesterBit('scowl'),
  dog: attesterBit('wiktionary'),
  zzz: Attested.Unchecked,
};
const attested = new Uint8Array(table.count);
const flags = new Uint8Array(table.count);
names.forEach((word, i) => {
  attested[i] = LISTED[word] ?? 0;
  if (word.startsWith('d')) flags[i] = WordFlag.Engine;
});
const meta = decodeMeta(encodeMeta(table.count, attested, new Uint16Array(table.count), flags));

const run = (patch: Partial<Query>) => {
  const result = runQuery(table, meta, { ...DEFAULT_QUERY, ...patch });
  return { words: Array.from(result.indices, (i) => wordAt(table, i)), error: result.error };
};

describe('match modes', () => {
  it('prefix', () => {
    expect(run({ text: 'c', mode: 'prefix' }).words).toEqual(['cart', 'cat', 'cot', 'cut']);
  });

  it('contains', () => {
    expect(run({ text: 'og', mode: 'contains' }).words).toEqual(['dog', 'dogs']);
  });

  it('suffix', () => {
    expect(run({ text: 't', mode: 'suffix' }).words).toEqual(['cart', 'cat', 'cot', 'cut']);
  });

  it('pattern: _ is one byte', () => {
    expect(run({ text: 'c_t', mode: 'pattern' }).words).toEqual(['cat', 'cot', 'cut']);
  });

  it('pattern: * is any run, including empty', () => {
    expect(run({ text: 'd*', mode: 'pattern' }).words).toEqual(['dog', 'dogs']);
    expect(run({ text: '*o*', mode: 'pattern' }).words).toEqual(['cot', 'dog', 'dogs', 'norteño']);
  });

  it('regex', () => {
    expect(run({ text: '^c.t$', mode: 'regex' }).words).toEqual(['cat', 'cot', 'cut']);
  });

  it('reports an unparseable regex instead of returning nothing', () => {
    const result = run({ text: '[', mode: 'regex' });
    expect(result.words).toEqual([]);
    expect(result.error).toBeTruthy();
  });

  it('empty text matches everything', () => {
    expect(run({ text: '' }).words).toHaveLength(WORDS.length);
  });
});

describe('filters', () => {
  it('length bounds are inclusive and count bytes', () => {
    expect(run({ minLength: 3, maxLength: 3 }).words).toEqual(['cat', 'cot', 'cut', 'dog', 'zzz']);
  });

  it('the synthetic engine', () => {
    expect(run({ engine: 'only' }).words).toEqual(['dog', 'dogs']);
    expect(run({ engine: 'without' }).words).not.toContain('dog');
    expect(run({ engine: 'without' }).words).toHaveLength(WORDS.length - 2);
  });

  it('listed by any of the chosen sources', () => {
    expect(run({ listedBy: ['scowl'] }).words).toEqual(['cat', 'cut']);
    expect(run({ listedBy: ['wordnet', 'scowl'] }).words).toEqual(['cat', 'cot', 'cut']);
    expect(run({ listedBy: ['enable'] }).words).toEqual([]);
  });

  it('listed by no open source, and not checked yet, are separate', () => {
    expect(run({ listedBy: ['none'] }).words).toEqual(['ad-lib', 'cart', 'dogs', 'norteño']);
    expect(run({ listedBy: ['unchecked'] }).words).toEqual(['zzz']);
    expect(run({ listedBy: ['unchecked', 'wordnet'] }).words).toEqual(['cot', 'zzz']);
  });

  it('filters by first letter', () => {
    expect(run({ letters: ['d'] }).words).toEqual(['dog', 'dogs']);
  });

  // Every word in the real list begins with a-z: `-` is 0x2D and would sort
  // ahead of `a`, and the list starts with `a`. Hyphens and accents are always
  // internal, which is why they are a whole-word filter and not a first-letter
  // one.
  it('finds hyphens and accents wherever they sit in the word', () => {
    expect(run({ charset: 'hyphen' }).words).toEqual(['ad-lib']);
    expect(run({ charset: 'accent' }).words).toEqual(['norteño']);
  });

  it('`alpha` excludes both', () => {
    const words = run({ charset: 'alpha' }).words;
    expect(words).not.toContain('ad-lib');
    expect(words).not.toContain('norteño');
    expect(words).toContain('cat');
  });

  it('`any` is the default and excludes nothing', () => {
    expect(run({ charset: 'any' }).words).toHaveLength(WORDS.length);
  });

  it('combines filters', () => {
    expect(run({ engine: 'only', maxLength: 3 }).words).toEqual(['dog']);
    expect(run({ engine: 'only', listedBy: ['none'] }).words).toEqual(['dogs']);
  });
});

describe('sorting', () => {
  it('alphabetical is the default and ascending', () => {
    expect(run({}).words[0]).toBe('ad-lib');
  });

  it('descending reverses', () => {
    const ascending = run({}).words;
    expect(run({ descending: true }).words).toEqual([...ascending].reverse());
  });

  it('length sorts short first and breaks ties alphabetically', () => {
    expect(run({ sort: 'length' }).words.slice(0, 6)).toEqual([
      'cat',
      'cot',
      'cut',
      'dog',
      'zzz',
      'cart',
    ]);
  });

  it('a length sort stays stable across repeated runs', () => {
    expect(run({ sort: 'length' }).words).toEqual(run({ sort: 'length' }).words);
  });
});
