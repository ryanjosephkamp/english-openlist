import { useState } from 'react';
import type { Stats } from '../../state/useStats.ts';
import { Figure, Readout, ChartScroll } from './Figure.tsx';
import { n } from '../../util/format.ts';

const W = 720;
const H = 240;
const PAD = { top: 12, right: 8, bottom: 26, left: 44 };

/**
 * Word length, as columns.
 *
 * One series, so no legend — the title names it. Columns rather than a line
 * because length is a count of discrete buckets, and a line would imply you can
 * read a value between 9 and 10 letters.
 */
export function LengthChart({ stats }: { stats: Stats }) {
  const [hover, setHover] = useState<number | null>(null);

  const data = stats.lengths;
  const maxCount = Math.max(...data.map((d) => d.count));
  const maxLength = Math.max(...data.map((d) => d.length));
  const total = data.reduce((sum, d) => sum + d.count, 0);

  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const step = plotW / maxLength;
  // 2px of surface between neighbours, per the mark spec — never touching bars.
  const barW = Math.max(1, step - 2);

  const x = (length: number) => PAD.left + (length - 1) * step;
  const y = (count: number) => PAD.top + plotH - (count / maxCount) * plotH;

  const peak = data.reduce((best, d) => (d.count > best.count ? d : best), data[0]!);
  const active = hover !== null ? data.find((d) => d.length === hover) : undefined;

  // Computed rather than asserted. The claim in the lede has to stay true as the
  // list changes, and a sentence nobody recalculates is a sentence that goes
  // quietly wrong.
  let seen = 0;
  const median = data.find((d) => (seen += d.count) >= total / 2)!.length;
  const long = data.filter((d) => d.length >= 20).reduce((sum, d) => sum + d.count, 0);

  const ticks = [0, 10_000, 20_000, 30_000, 40_000].filter((t) => t <= maxCount);

  return (
    <Figure
      title="How long the words are"
      lede={`Lengths run from 1 to ${maxLength}. The distribution peaks at ${peak.length} letters and has a long, thin tail — half the list is ${median} letters or fewer, but ${n(long)} words run to 20 or more.`}
      note={
        <>
          The single longest is{' '}
          <a
            href="/word/phosphoribosylaminoimidazolesuccinocarboxamides"
            className="font-mono text-[13px] underline decoration-rule-strong underline-offset-4 transition-colors duration-150 hover:text-accent hover:decoration-accent"
          >
            phosphoribosylaminoimidazolesuccinocarboxamides
          </a>{' '}
          at {maxLength} letters.
        </>
      }
      table={{
        columns: ['Letters', 'Words', 'Share'],
        rows: data.map((d) => [d.length, d.count, `${((d.count / total) * 100).toFixed(2)}%`]),
      }}
    >
      <Readout>
        {active ? (
          <>
            <span className="text-ink">{active.length} letters</span>
            <span>
              {n(active.count)} words · {((active.count / total) * 100).toFixed(2)}%
            </span>
          </>
        ) : (
          <span className="text-ink-faint">Hover a column for its exact count</span>
        )}
      </Readout>

      <ChartScroll minWidth={560}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="mt-1 w-full"
        role="img"
        aria-label={`Column chart of word length. Peak at ${peak.length} letters with ${n(peak.count)} words.`}
        onPointerLeave={() => setHover(null)}
      >
        {ticks.map((t) => (
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
              {t === 0 ? '0' : `${t / 1000}k`}
            </text>
          </g>
        ))}

        {data.map((d) => {
          const on = hover === d.length;
          return (
            <rect
              key={d.length}
              x={x(d.length)}
              y={y(d.count)}
              width={barW}
              height={PAD.top + plotH - y(d.count)}
              fill={on ? 'var(--color-accent-hover)' : 'var(--color-accent)'}
              rx="1"
            />
          );
        })}

        {/* Hit targets are full-height and wider than the bars, so a 1px column
            at length 41 is still reachable with a pointer. */}
        {data.map((d) => (
          <rect
            key={`hit-${d.length}`}
            x={x(d.length) - 1}
            y={PAD.top}
            width={step + 2}
            height={plotH}
            fill="transparent"
            onPointerEnter={() => setHover(d.length)}
          />
        ))}

        <line
          x1={PAD.left}
          x2={W - PAD.right}
          y1={PAD.top + plotH}
          y2={PAD.top + plotH}
          stroke="var(--color-rule-strong)"
          strokeWidth="1"
        />

        {[1, 5, 10, 15, 20, 25, 30, 35, 40, 45].map((t) => (
          <text
            key={t}
            x={x(t) + barW / 2}
            y={H - 8}
            textAnchor="middle"
            className="fill-ink-faint font-mono"
            fontSize="10"
          >
            {t}
          </text>
        ))}
      </svg>
      </ChartScroll>
    </Figure>
  );
}
