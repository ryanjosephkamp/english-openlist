import { useEffect, useId, useRef, useState } from 'react';
import { compact, plural, ticks } from './format';

export interface NightlyRun {
  /** `YYYY-MM-DD` */
  readonly date: string;
  readonly added: number;
  /** the run failed before it read the list */
  readonly failed?: boolean;
}

interface Props {
  /** the runs from `from` to `to`, oldest first */
  readonly runs: readonly NightlyRun[];
  readonly from: string;
  readonly to: string;
  readonly label: string;
  /** the daily log's address: a run's page is this, its date, and a slash */
  readonly base: string;
  readonly height?: number;
}

const DAY = 86_400_000;
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const parse = (iso: string) => Date.UTC(Number(iso.slice(0, 4)), Number(iso.slice(5, 7)) - 1, Number(iso.slice(8, 10)));
const longDate = (iso: string) => `${MONTHS[Number(iso.slice(5, 7)) - 1]} ${Number(iso.slice(8))}, ${iso.slice(0, 4)}`;
const shortDate = (t: number) => {
  const d = new Date(t);
  return `${MONTHS[d.getUTCMonth()]!.slice(0, 3)} ${d.getUTCDate()}`;
};
/** A run of days with no run at all, this long or longer, is drawn and named. */
const GAP_DAYS = 7;

function what(run: NightlyRun): string {
  if (run.failed) return 'The run failed';
  return run.added === 0 ? 'No words added' : `${plural(run.added, 'word')} added`;
}

/**
 * The nightly run's additions on a calendar axis: 1 slot a day, so a week with
 * no run reads as a week, not as the next column. A run that added nothing is a
 * mark on the baseline; a day with no run is empty. Hovering a run previews it,
 * and choosing it opens a card that links to its page in the daily log.
 */
export default function Nightly({ runs, from, to, label, base, height = 150 }: Props) {
  const [hover, setHover] = useState<number | null>(null);
  const [open, setOpen] = useState<number | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const plot = useRef<HTMLDivElement>(null);
  const link = useRef<HTMLAnchorElement>(null);
  const id = useId();

  const start = parse(from);
  const days = Math.round((parse(to) - start) / DAY) + 1;
  const slot = (iso: string) => Math.round((parse(iso) - start) / DAY);
  const max = Math.max(1, ...runs.map((r) => r.added));
  const scale = ticks(max, 3);
  const top = scale[scale.length - 1]!;

  // Days with no run, in spans long enough to name.
  const ran = new Set(runs.map((r) => slot(r.date)));
  const gaps: { at: number; length: number }[] = [];
  for (let d = 0; d < days; ) {
    if (ran.has(d)) {
      d++;
      continue;
    }
    let e = d;
    while (e < days && !ran.has(e)) e++;
    if (e - d >= GAP_DAYS) gaps.push({ at: d, length: e - d });
    d = e;
  }

  // Axis labels on the 1st and the 15th of each month in range.
  const labels: { at: number; text: string }[] = [];
  for (let d = 0; d < days; d++) {
    const t = start + d * DAY;
    const day = new Date(t).getUTCDate();
    if (day === 1 || day === 15) labels.push({ at: d, text: shortDate(t) });
  }

  // An open card closes on Escape, or on a press anywhere outside the chart.
  useEffect(() => {
    if (open === null) return;
    link.current?.focus({ preventScroll: true });
    const away = (e: PointerEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(null);
    };
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        const bar = root.current?.querySelector<HTMLButtonElement>(`[data-run="${open}"]`);
        setOpen(null);
        bar?.focus();
      }
    };
    document.addEventListener('pointerdown', away);
    document.addEventListener('keydown', key);
    return () => {
      document.removeEventListener('pointerdown', away);
      document.removeEventListener('keydown', key);
    };
  }, [open]);

  // A pointer picks the nearest run within a few days, so a run is as easy to
  // reach on a phone as on a desktop, though its column may be 4 pixels wide.
  const nearest = (clientX: number): number | null => {
    const box = plot.current?.getBoundingClientRect();
    if (!box || box.width === 0) return null;
    const at = ((clientX - box.left) / box.width) * days - 0.5;
    let best: number | null = null;
    let gap = 3.5;
    runs.forEach((r, i) => {
      const g = Math.abs(slot(r.date) - at);
      if (g < gap) [best, gap] = [i, g];
    });
    return best;
  };

  const shown = open ?? hover;
  const run = shown === null ? null : runs[shown]!;
  const x = (d: number) => ((d + 0.5) / days) * 100;

  return (
    <div className="nightly" ref={root} style={{ ['--h' as string]: `${height}px` }}>
      <div
        className="cols-plot"
        ref={plot}
        onPointerMove={(e) => setHover(nearest(e.clientX))}
        onPointerLeave={() => setHover(null)}
        onClick={(e) => {
          if ((e.target as Element).closest('.nightly-card')) return;
          // A keyboard press on a run's button arrives as a click with no position.
          const i =
            e.detail === 0
              ? Number((e.target as Element).closest<HTMLElement>('[data-run]')?.dataset['run'] ?? NaN)
              : nearest(e.clientX);
          if (i === null || Number.isNaN(i)) return;
          setOpen((o) => (o === i ? null : i));
        }}
      >
        <div className="cols-grid" aria-hidden="true">
          {scale.map((t) => (
            <span key={t} className="cols-tick" style={{ bottom: `${(100 * t) / top}%` }}>
              <span className="cols-tick-label">{compact(t)}</span>
            </span>
          ))}
        </div>
        {gaps.map((g) => (
          <span
            key={g.at}
            className="nightly-gap"
            style={{ left: `${(g.at / days) * 100}%`, width: `${(g.length / days) * 100}%` }}
          >
            <span>No runs</span>
          </span>
        ))}
        <ol className="nightly-runs" aria-label={label}>
          {runs.map((r, i) => {
            const d = slot(r.date);
            const h = r.added > 0 ? Math.max(2, (100 * r.added) / top) : 0;
            return (
              <li key={r.date} style={{ left: `${(d / days) * 100}%`, width: `${100 / days}%` }}>
                <button
                  type="button"
                  className={`nightly-hit${shown === i ? ' is-on' : ''}`}
                  data-run={i}
                  aria-label={`${longDate(r.date)}: ${what(r)}`}
                  aria-expanded={open === i}
                  aria-controls={open === i ? `${id}-card` : undefined}
                  onFocus={() => setHover(i)}
                  onBlur={() => setHover(null)}
                >
                  {r.added > 0 ? (
                    <span className="nightly-bar" style={{ height: `${h}%` }} />
                  ) : (
                    <span className={`nightly-zero${r.failed ? ' is-failed' : ''}`} />
                  )}
                </button>
              </li>
            );
          })}
        </ol>
        {run && shown !== null && (
          <div
            id={open !== null ? `${id}-card` : undefined}
            className={`tip nightly-card${open !== null ? ' is-open' : ''}`}
            role={open !== null ? 'group' : 'presentation'}
            aria-label={open !== null ? longDate(run.date) : undefined}
            style={{ left: `clamp(5.5rem, ${x(slot(run.date))}%, calc(100% - 5.5rem))` }}
          >
            <strong>{what(run)}</strong>
            <span>{longDate(run.date)}</span>
            {open !== null ? (
              <a ref={link} href={`${base}${run.date}/`}>
                Read the day's log
              </a>
            ) : (
              <span className="nightly-hint">Select it for the day's log</span>
            )}
          </div>
        )}
      </div>
      <div className="nightly-axis" aria-hidden="true">
        {labels.map((l) => (
          <span key={l.at} style={{ left: `clamp(1.25rem, ${x(l.at)}%, calc(100% - 1.25rem))` }}>
            {l.text}
          </span>
        ))}
      </div>
    </div>
  );
}
