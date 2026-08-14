import { describe, expect, it } from 'vitest';
import { encodeWords, encodeMeta, compareBytes, INTAKE, WordFlag } from './format.ts';
import { decodeWords, decodeMeta, wordAt } from './decode.ts';
import { runQuery, DEFAULT_QUERY, type Query } from './query.ts';

const encoder = new TextEncoder();

const WORDS = ['cat', 'cot', 'cut', 'cart', 'dog', 'dogs', 'zzz', 'ad-lib', 'norteño']
  .map((w) => encoder.encode(w))
  .sort(compareBytes);

const table = decodeWords(encodeWords(WORDS));
const names = Array.from({ length: table.count }, (_, i) => wordAt(table, i));

// Intake and flags assigned by position so the filters have something to bite on.
const intake = new Uint8Array(table.count);
const flags = new Uint8Array(table.count);
names.forEach((word, i) => {
  intake[i] = word.startsWith('d') ? INTAKE.synthetic : INTAKE.twl;
  if (word === 'zzz') flags[i] = WordFlag.LlmSaysInvalid;
});
const meta = decodeMeta(encodeMeta(table.count, intake, new Uint16Array(table.count), flags));

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

  it('intake', () => {
    expect(run({ intakes: ['synthetic'] }).words).toEqual(['dog', 'dogs']);
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

  it('hiding contested entries drops the flagged word', () => {
    expect(run({ includeContested: false }).words).not.toContain('zzz');
    expect(run({ includeContested: true }).words).toContain('zzz');
  });

  it('combines filters', () => {
    expect(run({ intakes: ['synthetic'], maxLength: 3 }).words).toEqual(['dog']);
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
