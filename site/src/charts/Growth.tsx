import { useEffect, useRef, useState } from 'react';
import { full } from './format';

export interface Point {
  readonly date: string;
  readonly total: number;
}

interface Props {
  readonly points: readonly Point[];
  /** the days the total moved by more than `markOver` words, labeled on the line */
  readonly marks: readonly { date: string; label: string }[];
  readonly label: string;
  /** the axis's floor; the chart says it is not 0 */
  readonly floor: number;
  readonly ceiling: number;
}

const H = 240;
const M = { top: 16, right: 16, bottom: 30, left: 64 };
const DAY = 86_400_000;
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const t = (iso: string) => Date.parse(`${iso}T00:00:00Z`);
const day = (ms: number) => {
  const d = new Date(ms);
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
};

/**
 * The list's size over the recorded days, as a step line: the size holds until
 * the day it changes. The axis does not start at 0, and says so, because the
 * size moved by tens of words for months and by tens of thousands in 1 day.
 */
export default function Growth({ points, marks, label, floor, ceiling }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const [W, setW] = useState(640);
  const [at, setAt] = useState<number | null>(null);
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(280, Math.round(e!.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const x0 = t(points[0]!.date);
  const x1 = t(points[points.length - 1]!.date);
  const iw = W - M.left - M.right;
  const ih = H - M.top - M.bottom;
  const x = (ms: number) => M.left + ((ms - x0) / Math.max(DAY, x1 - x0)) * iw;
  const y = (v: number) => M.top + (1 - (v - floor) / (ceiling - floor)) * ih;

  let d = '';
  points.forEach((p, i) => {
    const px = x(t(p.date));
    const py = y(p.total);
    if (i === 0) d += `M${px},${py}`;
    else d += `H${px}V${py}`;
  });

  const step = (ceiling - floor) / 4;
  const yTicks = [0, 1, 2, 3, 4].map((k) => floor + k * step);
  const months: number[] = [];
  const start = new Date(x0);
  for (let m = new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 1)).getTime(); m <= x1; ) {
    months.push(m);
    const dm = new Date(m);
    m = Date.UTC(dm.getUTCFullYear(), dm.getUTCMonth() + 1, 1);
  }

  const hover = at === null ? null : points[at]!;
  const pick = (clientX: number, svg: SVGSVGElement) => {
    const r = svg.getBoundingClientRect();
    const ms = x0 + ((clientX - r.left - M.left) / iw) * (x1 - x0);
    let best = 0;
    for (let i = 0; i < points.length; i++) if (t(points[i]!.date) <= ms) best = i;
    setAt(best);
  };

  return (
    <div className="growth" ref={box}>
      <svg
        width={W}
        height={H}
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={label}
        onPointerMove={(e) => pick(e.clientX, e.currentTarget)}
        onPointerLeave={() => setAt(null)}
      >
        {yTicks.map((v) => (
          <g key={v}>
            <line className="g-grid" x1={M.left} x2={W - M.right} y1={y(v)} y2={y(v)} />
            <text className="g-tick" x={M.left - 8} y={y(v)} dy="0.32em" textAnchor="end">
              {full(v)}
            </text>
          </g>
        ))}
        {months.map((m) => (
          <text key={m} className="g-tick" x={x(m)} y={H - 8} textAnchor="middle">
            {MONTHS[new Date(m).getUTCMonth()]}
          </text>
        ))}
        <path className="g-line" d={d} />
        {marks.map((mk) => {
          const p = points.find((q) => q.date === mk.date);
          if (!p) return null;
          const px = x(t(p.date));
          const right = px > W * 0.6;
          return (
            <g key={mk.date}>
              <circle className="g-dot" cx={px} cy={y(p.total)} r={3.5} />
              <text className="g-mark" x={px + (right ? -8 : 8)} y={y(p.total) - 10} textAnchor={right ? 'end' : 'start'}>
                {mk.label}
              </text>
            </g>
          );
        })}
        {hover && (
          <g>
            <line className="g-cross" x1={x(t(hover.date))} x2={x(t(hover.date))} y1={M.top} y2={H - M.bottom} />
            <circle className="g-dot" cx={x(t(hover.date))} cy={y(hover.total)} r={4} />
          </g>
        )}
      </svg>
      <p className="growth-read" aria-live="polite">
        {hover ? (
          <>
            <strong>{full(hover.total)}</strong> words on {day(t(hover.date))}
          </>
        ) : (
          <>The axis starts at {full(floor)}, not at 0.</>
        )}
      </p>
    </div>
  );
}
