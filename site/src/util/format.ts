import { INTAKE_NAMES } from '@eol/wordlist/format';

export const n = (value: number): string => value.toLocaleString('en-US');

export function bytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}

/**
 * Report a duration the way the reader experiences it.
 *
 * Sub-millisecond scans are the common case on prefix queries, and printing
 * "0ms" reads as a missing measurement rather than a fast one.
 */
export function millis(value: number): string {
  if (value < 1) return '<1 ms';
  return `${Math.round(value)} ms`;
}

export const INTAKE_LABEL: Record<string, string> = {
  twl: 'Tournament list',
  pipeline: 'Verification pipeline',
  synthetic: 'Synthetic',
  other: 'Other',
};

/** The one-line account of what an intake actually means. */
export const INTAKE_NOTE: Record<string, string> = {
  twl: 'From the tournament Scrabble word list.',
  pipeline: 'Attested by open corpora, then checked by the validation pipeline.',
  synthetic: 'Constructed algorithmically, then validated. The group most likely to surprise you.',
  other: 'Assembled from earlier intakes that recorded less about themselves.',
};

export function intakeName(code: number): string {
  return INTAKE_NAMES[code] ?? 'other';
}

export function intakeLabel(code: number): string {
  return INTAKE_LABEL[intakeName(code)] ?? 'Other';
}
