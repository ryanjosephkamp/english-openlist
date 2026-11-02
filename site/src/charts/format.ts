/** Number formats for the charts: full counts in labels and tables, compact
 *  ones on axes. */

export const full = (n: number) => Math.round(n).toLocaleString('en-US');

export function compact(n: number): string {
  const a = Math.abs(n);
  if (a >= 1e6) return `${trim(n / 1e6)}M`;
  if (a >= 1e3) return `${trim(n / 1e3)}K`;
  return String(Math.round(n));
}

function trim(x: number): string {
  const s = x >= 100 ? x.toFixed(0) : x >= 10 ? x.toFixed(1) : x.toFixed(2);
  return s.replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1');
}

/** A count with its noun: "1 letter", "2 letters". The plural is the singular
 *  with an s unless `many` names it. */
export function plural(n: number, one: string, many = `${one}s`): string {
  return `${full(n)} ${n === 1 ? one : many}`;
}

/** A share as a percentage, with enough digits that a small share is not
 *  shown as 0. */
export function pct(part: number, whole: number): string {
  if (!whole) return '0%';
  const p = (100 * part) / whole;
  if (p === 0) return '0%';
  if (p >= 10) return `${p.toFixed(1)}%`;
  if (p >= 0.01) return `${p.toFixed(2)}%`;
  return '<0.01%';
}

/** Clean axis ticks from 0 to at least `max`. */
export function ticks(max: number, count = 4): number[] {
  if (max <= 0) return [0];
  const raw = max / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
  const out: number[] = [];
  for (let v = 0; v <= max + step * 0.0001; v += step) out.push(v);
  if (out[out.length - 1] < max) out.push(out[out.length - 1] + step);
  return out;
}
