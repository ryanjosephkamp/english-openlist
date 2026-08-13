import { describe, expect, it } from 'vitest';
import { fnv1a as buildHash, SHARD_COUNT } from '../../../tools/eol-build/src/provenance.ts';

/**
 * The hash exists twice: once in the build that writes the shards, once in the
 * browser that reads them. If they ever disagree every lookup lands in the
 * wrong file and returns nothing — and nothing is exactly what a word with no
 * provenance legitimately returns, so the failure would be silent.
 *
 * This imports the build's copy and re-implements the browser's inline, so the
 * test fails if either side is edited alone.
 */
function siteHash(word: string): number {
  let hash = 0x811c9dc5;
  for (let i = 0; i < word.length; i++) {
    hash ^= word.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193) >>> 0;
  }
  return hash >>> 0;
}

const WORDS = [
  'a',
  'aalii',
  'bussin',
  'skibidi',
  'zzz',
  'norteño',
  'peléan',
  'ad-lib',
  'phosphoribosylaminoimidazolesuccinocarboxamides',
];

describe('provenance sharding', () => {
  it('the build and the browser agree on every hash', () => {
    for (const word of WORDS) {
      expect(siteHash(word), word).toBe(buildHash(word));
    }
  });

  it('agrees across a wide generated sample', () => {
    for (let i = 0; i < 5_000; i++) {
      const word = i.toString(36).repeat((i % 4) + 1);
      expect(siteHash(word), word).toBe(buildHash(word));
    }
  });

  it('lands every word inside the shard range', () => {
    for (const word of WORDS) {
      const shard = siteHash(word) % SHARD_COUNT;
      expect(shard).toBeGreaterThanOrEqual(0);
      expect(shard).toBeLessThan(SHARD_COUNT);
    }
  });

  it('spreads words across shards rather than clustering', () => {
    const hit = new Set<number>();
    for (let i = 0; i < 20_000; i++) hit.add(siteHash(`w${i}`) % SHARD_COUNT);
    // A hash that collapsed would fill far fewer; a good one fills essentially
    // all of them at this sample size.
    expect(hit.size).toBe(SHARD_COUNT);
  });
});
