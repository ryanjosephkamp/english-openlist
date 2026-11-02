import { full, pct } from './format';

export interface Bar {
  readonly key: string;
  readonly label: string;
  readonly value: number;
  /** the bar's color role; muted for a bar that is not a channel or a value */
  readonly tone?: 'accent' | 'eol' | 'muted';
  readonly title?: string;
}

interface Props {
  readonly bars: readonly Bar[];
  /** the whole the shares are of */
  readonly total: number;
  /** the scale's top; the largest bar by default */
  readonly max?: number;
  /** the keys a filter holds; the other bars recede while any is held */
  readonly selected?: ReadonlySet<string>;
  /** makes each bar a toggle */
  readonly onToggle?: (key: string) => void;
  readonly label: string;
  /** the bars' color role unless a bar names its own */
  readonly tone?: 'accent' | 'eol';
}

/**
 * Horizontal bars for a breakdown, 1 series: a label, the bar from 1
 * baseline, and the value with its share at the tip. With `onToggle` each
 * bar is a button that adds or removes its value from a filter.
 */
export default function BarList({ bars, total, max, selected, onToggle, label, tone: listTone = 'accent' }: Props) {
  const top = max ?? Math.max(1, ...bars.map((b) => b.value));
  const holding = !!selected && selected.size > 0;
  return (
    <ul className={`barlist${onToggle ? ' is-interactive' : ''}`} aria-label={label}>
      {bars.map((b) => {
        const on = selected?.has(b.key) ?? false;
        // a toggle that would add no rows is shown but not offered
        const zero = b.value === 0 && !on;
        const w = b.value > 0 ? Math.max(0.6, (100 * b.value) / top) : 0;
        const tone = holding && !on ? 'muted' : (b.tone ?? listTone);
        const body = (
          <>
            <span className="bl-label">{b.label}</span>
            <span className="bl-track" aria-hidden="true">
              <span className={`bl-bar t-${tone}`} style={{ width: `${w}%` }} />
            </span>
            <span className="bl-value">
              <span className="bl-n">{full(b.value)}</span>
              <span className="bl-pct">{pct(b.value, total)}</span>
            </span>
          </>
        );
        return (
          <li key={b.key} className={on ? 'is-on' : zero ? 'is-zero' : undefined}>
            {onToggle ? (
              <button
                type="button"
                className="bl-row"
                aria-pressed={on}
                disabled={zero}
                title={b.title}
                onClick={() => onToggle(b.key)}
              >
                {body}
              </button>
            ) : (
              <div className="bl-row" title={b.title}>
                {body}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
