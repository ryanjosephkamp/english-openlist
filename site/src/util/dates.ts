/** Dates as a reader sees them: October 25, 2026. */

const LONG = new Intl.DateTimeFormat('en-US', { month: 'long', day: 'numeric', year: 'numeric' });

/** A date, or an ISO day (2026-10-25) read as that calendar day wherever
 *  the reader is. */
export function usDate(d: Date | string): string {
  if (typeof d === 'string') {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(d);
    if (!m) throw new Error(`not an ISO day: ${d}`);
    return LONG.format(new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  }
  return LONG.format(d);
}
