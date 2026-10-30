import { describe, expect, it } from 'vitest';
import { plural } from './format';

describe('plural', () => {
  it('uses the singular for 1 only', () => {
    expect(plural(1, 'letter')).toBe('1 letter');
    expect(plural(0, 'letter')).toBe('0 letters');
    expect(plural(2, 'word')).toBe('2 words');
  });

  it('groups thousands and takes an irregular plural', () => {
    expect(plural(345162, 'word')).toBe('345,162 words');
    expect(plural(2, 'entry', 'entries')).toBe('2 entries');
  });
});
