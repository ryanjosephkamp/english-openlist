import { describe, expect, it } from 'vitest';
import { DEFAULT_QUERY, type Query } from '@eol/wordlist/query';
import { queryToParams, paramsToQuery, queryToUrl } from './urlState.ts';

const roundTrip = (query: Query) => paramsToQuery(queryToParams(query));

describe('url state', () => {
  it('writes nothing for the default query', () => {
    expect(queryToParams(DEFAULT_QUERY).toString()).toBe('');
    expect(queryToUrl('/', DEFAULT_QUERY)).toBe('/');
  });

  it('round-trips a fully specified query', () => {
    const query: Query = {
      text: 'zy',
      mode: 'contains',
      minLength: 4,
      maxLength: 12,
      intakes: ['twl', 'synthetic'],
      letters: ['a', 'z'],
      charset: 'hyphen',
      sort: 'length',
      descending: true,
      includeContested: false,
    };
    expect(roundTrip(query)).toEqual(query);
  });

  it('parses an empty search back to the default', () => {
    expect(paramsToQuery(new URLSearchParams(''))).toEqual(DEFAULT_QUERY);
  });

  it('writes spaces as %20 rather than +', () => {
    // `+` is correct for a form body and wrong-looking in a shared link.
    expect(queryToUrl('/', { ...DEFAULT_QUERY, text: 'ad lib' })).toBe('/?q=ad%20lib');
  });

  it('ignores a mode it does not recognise', () => {
    expect(paramsToQuery(new URLSearchParams('m=telepathy')).mode).toBe(DEFAULT_QUERY.mode);
  });

  it('ignores an out-of-range length', () => {
    expect(paramsToQuery(new URLSearchParams('min=0')).minLength).toBe(DEFAULT_QUERY.minLength);
    expect(paramsToQuery(new URLSearchParams('max=99')).maxLength).toBe(DEFAULT_QUERY.maxLength);
    expect(paramsToQuery(new URLSearchParams('min=abc')).minLength).toBe(DEFAULT_QUERY.minLength);
  });

  it('drops an intake that does not exist and keeps the rest', () => {
    expect(paramsToQuery(new URLSearchParams('i=twl,unicorn')).intakes).toEqual(['twl']);
  });

  it('normalises intake order so the same filter is the same URL', () => {
    // Parsed in the canonical order rather than the order typed, so two people
    // selecting the same two intakes share an identical link.
    expect(paramsToQuery(new URLSearchParams('i=synthetic,twl')).intakes).toEqual([
      'twl',
      'synthetic',
    ]);
  });

  it('drops a letter filter that is not a single a-z letter', () => {
    expect(paramsToQuery(new URLSearchParams('l=a,zz,3,-,other,z')).letters).toEqual(['a', 'z']);
  });

  it('ignores a charset it does not recognise', () => {
    expect(paramsToQuery(new URLSearchParams('ch=cyrillic')).charset).toBe(DEFAULT_QUERY.charset);
    expect(paramsToQuery(new URLSearchParams('ch=hyphen')).charset).toBe('hyphen');
  });

  it('treats any value but 0 as including contested entries', () => {
    expect(paramsToQuery(new URLSearchParams('c=0')).includeContested).toBe(false);
    expect(paramsToQuery(new URLSearchParams('c=1')).includeContested).toBe(true);
    expect(paramsToQuery(new URLSearchParams('')).includeContested).toBe(true);
  });
});
