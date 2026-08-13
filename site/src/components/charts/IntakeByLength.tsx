import { useState } from 'react';
import type { Stats } from '../../state/useStats.ts';
import { Figure, Readout, ChartScroll, INTAKE_FILL } from './Figure.tsx';
import { INTAKE_LABEL, n } from '../../util/format.ts';

const W = 720;
const H = 300;
const PAD = { top: 12, right: 8, bottom: 26, left: 44 };

/**
 * Below this many words a length's shares are noise, not signal — at 41 letters
 * the whole bucket is one word, and one word is either 0% or 100% synthetic.
 * The chart stops where the sample stops supporting it and says how much it left
 * out.
 */
const MIN_SAMPLE = 300;

/**
 * Stacked bottom to top as twl, pipeline, other, synthetic.
 *
 * Not the ramp's own order. Putting the three human-attested intakes together at
 * the bottom makes the top of the third band a single clean line — the share of
 * words at each length that some human source actually attested — which is the
 * question a reader of this dataset actually has. Re-validated in this order:
 * worst adjacent pair ΔE 15.3 normal, 14.6 deutan.
 */
const STACK = ['twl', 'pipeline', 'other', 'synthetic'] as const;
const INTAKE_INDEX: Record<string, number> = { twl: 0, pipeline: 1, synthetic: 2, other: 3 };

export function IntakeByLength({ stats }: { stats: Stats }) {
  const [hover, setHover] = useState<number | null>(null);

  const usable = stats.intakeByLength.filter((d) => d.total >= MIN_SAMPLE);
  const dropped = stats.intakeByLength.filter((d) => d.total < MIN_SAMPLE);
  const droppedWords = dropped.reduce((sum, d) => sum + d.total, 0);

  const minLength = usable[0]!.length;
  const maxLength = usable[usable.length - 1]!.length;

  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const x = (length: number) =>
    PAD.left + ((length - minLength) / (maxLength - minLength)) * plotW;
  const y = (share: number) => PAD.top + plotH - share * plotH;

  // Cumulative share boundaries per length, bottom of the stack upward.
  const boundaries = usable.map((d) => {
    let acc = 0;
    return {
      length: d.length,
      total: d.total,
      stops: STACK.map((name) => {
        acc += d.counts[INTAKE_INDEX[name]!]! / d.total;
        return acc;
      }),
    };
  });

  const band = (index: number) => {
    const lower = index === 0 ? usable.map(() => 0) : boundaries.map((b) => b.stops[index - 1]!);
    const upper = boundaries.map((b) => b.stops[index]!);
    const top = boundaries.map((b, i) => `${x(b.length)},${y(upper[i]!)}`).join(' L');
    const bottom = [...boundaries]
      .map((b, i) => ({ b, i }))
      .reverse()
      .map(({ b, i }) => `${x(b.length)},${y(lower[i]!)}`)
      .join(' L');
    return `M${top} L${bottom} Z`;
  };

  const active = hover !== null ? boundaries.find((b) => b.length === hover) : undefined;
  const activeRow = active ? usable.find((d) => d.length === active.length)! : undefined;
  const humanShare = (d: (typeof usable)[number]) =>
    (d.counts[0]! + d.counts[1]! + d.counts[3]!) / d.total;

  const shortest = usable[0]!;
  const longest = usable[usable.length - 1]!;

  return (
    <Figure
      title="Where a word came from, by how long it is"
      lede={`The single most useful thing to know before using this list. At ${shortest.length} letters, ${(humanShare(shortest) * 100).toFixed(1)}% of words were attested by a human source. At ${longest.length} letters that has fallen to ${(humanShare(longest) * 100).toFixed(1)}% — the rest were constructed algorithmically.`}
      note={
        <>
          Lengths above {maxLength} are left out: together they hold {n(droppedWords)} words, and a
          bucket of a few dozen cannot support a percentage. The{' '}
          <a
            href="/?i=synthetic"
            className="underline decoration-rule-strong underline-offset-4 transition-colors duration-150 hover:text-accent hover:decoration-accent"
          >
            64,837 synthetic entries
          </a>{' '}
          are kept in the dataset deliberately — this is how to see where they are.
        </>
      }
      table={{
        columns: ['Letters', 'Words', 'Tournament', 'Pipeline', 'Other', 'Synthetic'],
        rows: usable.map((d) => [
          d.length,
          d.total,
          `${((d.counts[0]! / d.total) * 100).toFixed(1)}%`,
          `${((d.counts[1]! / d.total) * 100).toFixed(1)}%`,
          `${((d.counts[3]! / d.total) * 100).toFixed(1)}%`,
          `${((d.counts[2]! / d.total) * 100).toFixed(1)}%`,
        ]),
      }}
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
        {STACK.map((name) => (
          <span key={name} className="flex items-center gap-1.5 text-[11px] text-ink-soft">
            <span
              aria-hidden
              className="inline-block h-2.5 w-2.5 rounded-[1px] ring-1 ring-rule"
              style={{ background: INTAKE_FILL[name] }}
            />
            {INTAKE_LABEL[name]}
          </span>
        ))}
      </div>

      <Readout>
        {activeRow ? (
          <>
            <span className="text-ink">{activeRow.length} letters</span>
            <span>
              {n(activeRow.total)} words · {(humanShare(activeRow) * 100).toFixed(1)}% human-attested
              · {((activeRow.counts[2]! / activeRow.total) * 100).toFixed(1)}% synthetic
            </span>
          </>
        ) : (
          <span className="text-ink-faint">Hover to read a length</span>
        )}
      </Readout>

      <ChartScroll minWidth={560}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="mt-1 w-full"
        role="img"
        aria-label={`Stacked area chart of intake share by word length, ${minLength} to ${maxLength} letters. The synthetic share rises from ${((shortest.counts[2]! / shortest.total) * 100).toFixed(1)}% to ${((longest.counts[2]! / longest.total) * 100).toFixed(1)}%.`}
        onPointerLeave={() => setHover(null)}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={y(t)}
              y2={y(t)}
              stroke="var(--color-rule)"
              strokeWidth="1"
            />
            <text
              x={PAD.left - 8}
              y={y(t) + 3.5}
              textAnchor="end"
              className="fill-ink-faint font-mono"
              fontSize="10"
            >
              {t * 100}%
            </text>
          </g>
        ))}

        {/* Bands are stroked in the surface colour so neighbours never touch —
            the 2px separation the mark spec asks for, on an area rather than bars. */}
        {STACK.map((name, i) => (
          <path
            key={name}
            d={band(i)}
            fill={INTAKE_FILL[name]}
            stroke="var(--color-surface)"
            strokeWidth="2"
          />
        ))}

        {active && (
          <line
            x1={x(active.length)}
            x2={x(active.length)}
            y1={PAD.top}
            y2={PAD.top + plotH}
            stroke="var(--color-ink)"
            strokeWidth="1"
          />
        )}

        {boundaries.map((b) => (
          <rect
            key={`hit-${b.length}`}
            x={x(b.length) - plotW / (usable.length - 1) / 2}
            y={PAD.top}
            width={plotW / (usable.length - 1)}
            height={plotH}
            fill="transparent"
            onPointerEnter={() => setHover(b.length)}
          />
        ))}

        {usable
          .filter((d) => d.length % 4 === 0 || d.length === minLength || d.length === maxLength)
          .map((d) => (
            <text
              key={d.length}
              x={x(d.length)}
              y={H - 8}
              textAnchor="middle"
              className="fill-ink-faint font-mono"
              fontSize="10"
            >
              {d.length}
            </text>
          ))}
      </svg>
      </ChartScroll>
    </Figure>
  );
}
