/**
 * Which open sources list a word, in words: shared by the search, the word
 * panel, and the pages. Safe to load in the browser.
 */
import { Attested, attestersOf } from '@eol/wordlist/format';
import { ATTESTER_INFO } from '@eol/wordlist/sources';
import type { ListedBy } from '@eol/wordlist/query';

/** What each listed-by state means, in a sentence. */
export const LISTED_WHAT = {
  listed: 'Each is an open word list or dictionary whose own files include this word.',
  none: 'None of the 6 open sources lists it. That says what those sources hold, not whether it is a word.',
  unchecked: 'The list has not checked it against the open sources yet.',
} as const;

/** The synthetic engine, in a sentence. */
export const ENGINE_WHAT =
  "The list's synthetic engine made it by rule, for example by adding a prefix or a suffix to a word already on the list.";

export type ListedState = 'listed' | 'none' | 'unchecked';

export function listedState(attested: number): ListedState {
  if ((attested & Attested.Unchecked) !== 0) return 'unchecked';
  return (attested & Attested.Sources) !== 0 ? 'listed' : 'none';
}

/** The names of the sources that list a word, in their order. */
export function listedLabels(attested: number): string[] {
  return attestersOf(attested).map((key) => ATTESTER_INFO[key].label);
}

/** A row's short summary: "Listed by 3 open sources", "No open source", or "Not checked yet". */
export function listedShort(attested: number): string {
  const state = listedState(attested);
  if (state === 'unchecked') return 'Not checked yet';
  const n = attestersOf(attested).length;
  if (n === 0) return 'No open source';
  return `Listed by ${n} open ${n === 1 ? 'source' : 'sources'}`;
}

/** The chip's tone class: deeper as more open sources list the word. */
export function listedTone(attested: number): string {
  const state = listedState(attested);
  if (state !== 'listed') return `l-${state}`;
  const n = attestersOf(attested).length;
  return n >= 5 ? 'l-most' : n >= 3 ? 'l-some' : 'l-few';
}

/** "A", "A and B", or "A, B, and C". */
export function joinNames(names: readonly string[]): string {
  if (names.length < 3) return names.join(' and ');
  return `${names.slice(0, -1).join(', ')}, and ${names[names.length - 1]}`;
}

/** A listed-by filter value's name: a source, or 1 of the 2 states with none. */
export function listedByLabel(value: ListedBy): string {
  if (value === 'none') return 'No open source lists it';
  if (value === 'unchecked') return 'Not checked yet';
  return ATTESTER_INFO[value].label;
}
