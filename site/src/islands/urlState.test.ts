import { describe, expect, it } from 'vitest';
import { DEFAULT_QUERY } from '@eol/wordlist/query';
import { paramsToQuery, queryToParams, queryToUrl } from './urlState';

describe('the query in the URL', () => {
  it('writes nothing for the default query', () => {
    expect(queryToUrl('/', DEFAULT_QUERY)).toBe('/');
  });

  it('round-trips every field it writes', () => {
    const query = {
      ...DEFAULT_QUERY,
      text: 'ship',
      mode: 'suffix' as const,
      minLength: 4,
      maxLength: 12,
      decided: ['engine' as const, 'none' as const],
      letters: ['s', 'h'],
      sort: 'length' as const,
      descending: true,
      includeContested: false,
    };
    const back = paramsToQuery(queryToParams(query));
    expect(back).toEqual({ ...query, decided: ['none', 'engine'], letters: ['h', 's'] });
  });

  it('drops values it does not know', () => {
    const back = paramsToQuery(new URLSearchParams('m=nope&by=tournament,engine&l=s,ss,1&min=0&max=999'));
    expect(back.mode).toBe(DEFAULT_QUERY.mode);
    expect(back.decided).toEqual(['engine']);
    expect(back.letters).toEqual(['s']);
    expect(back.minLength).toBe(DEFAULT_QUERY.minLength);
    expect(back.maxLength).toBe(DEFAULT_QUERY.maxLength);
  });

  it('encodes a space as %20', () => {
    expect(queryToUrl('/', { ...DEFAULT_QUERY, text: 'a b', mode: 'regex' })).toBe('/?q=a%20b&m=regex');
  });
});
