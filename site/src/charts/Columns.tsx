import { useState } from 'react';
import { compact, full, pct, plural, ticks } from './format';

export interface Column {
  readonly key: string;
  /** the axis label; the tooltip's too, unless `name` is given */
  readonly label: string;
  readonly name?: string;
  readonly value: number;
}

interface Props {
  readonly columns: readonly Column[];
  readonly total: number;
  readonly label: string;
  /** an axis label shown under every `labelEvery`-th column */
  readonly labelEvery?: number;
  /** the columns a filter holds; the others recede while any is held */
  readonly selected?: (i: number) => boolean;
  /** makes each column a button; `extend` is true with Shift held */
  readonly onPick?: (i: number, extend: boolean) => void;
  readonly tone?: 'accent' | 'eol';
  readonly height?: number;
  /** what a column counts, singular, for its accessible name */
  readonly unit?: string;
}

/**
 * Vertical columns over an ordered axis (a length, a count of lists), from 1
 * baseline, with hairline gridlines at clean ticks and a tooltip on hover
 * and on keyboard focus: the value first, then the bucket and its share.
 */
export default function Columns({
  columns,
  total,
  label,
  labelEvery = 1,
  selected,
  onPick,
  tone = 'accent',
  height = 176,
  unit = 'word',
}: Props) {
  const [active, setActive] = useState<number | null>(null);
  const max = Math.max(1, ...columns.map((c) => c.value));
  const scale = ticks(max, 4);
  const top = scale[scale.length - 1];
  const holding = !!selected && columns.some((_, i) => selected(i));
  const tip = active === null ? null : columns[active];
  const left = active === null ? 0 : ((active + 0.5) / columns.length) * 100;

  return (
    <div className="cols" style={{ ['--h' as string]: `${height}px` }}>
      <div className="cols-plot" onPointerLeave={() => setActive(null)}>
        <div className="cols-grid" aria-hidden="true">
          {scale.map((t) => (
            <span key={t} className="cols-tick" style={{ bottom: `${(100 * t) / top}%` }}>
              <span className="cols-tick-label">{compact(t)}</span>
            </span>
          ))}
        </div>
        <ol className="cols-bars" aria-label={label}>
          {columns.map((c, i) => {
            const on = selected?.(i) ?? false;
            const h = c.value > 0 ? Math.max(0.8, (100 * c.value) / top) : 0;
            const cls = `cols-bar t-${holding && !on ? 'muted' : tone}`;
            const name = `${c.name ?? c.label}: ${plural(c.value, unit)}, ${pct(c.value, total)}`;
            const inner = <span className={cls} style={{ height: `${h}%` }} />;
            return (
              <li key={c.key} className={on ? 'is-on' : undefined}>
                {onPick ? (
                  <button
                    type="button"
                    className="cols-hit"
                    aria-label={name}
                    aria-pressed={on}
                    onPointerEnter={() => setActive(i)}
                    onFocus={() => setActive(i)}
                    onBlur={() => setActive(null)}
                    onClick={(e) => onPick(i, e.shiftKey)}
                  >
                    {inner}
                  </button>
                ) : (
                  <span
                    className="cols-hit"
                    role="img"
                    aria-label={name}
                    tabIndex={0}
                    onPointerEnter={() => setActive(i)}
                    onFocus={() => setActive(i)}
                    onBlur={() => setActive(null)}
                  >
                    {inner}
                  </span>
                )}
              </li>
            );
          })}
        </ol>
        {tip && (
          <div
            className="tip"
            role="presentation"
            style={{ left: `clamp(4.5rem, ${left}%, calc(100% - 4.5rem))` }}
          >
            <strong>{full(tip.value)}</strong>
            <span>
              {tip.name ?? tip.label} · {pct(tip.value, total)}
            </span>
          </div>
        )}
      </div>
      <ol className="cols-axis" aria-hidden="true">
        {columns.map((c, i) => (
          <li key={c.key}>
            {i % labelEvery === 0 || (i === columns.length - 1 && (columns.length - 1) % labelEvery > labelEvery / 2) ? c.label : ''}
          </li>
        ))}
      </ol>
    </div>
  );
}
