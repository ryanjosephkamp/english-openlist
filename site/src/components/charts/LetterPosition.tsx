import { useState } from 'react';
import type { Stats } from '../../state/useStats.ts';
import { Figure, Readout } from './Figure.tsx';
import { n } from '../../util/format.ts';

const LETTERS = 'abcdefghijklmnopqrstuvwxyz'.split('');
const CELL = 26;
const GAP = 2;
const LABEL_W = 22;
const HEADER_H = 18;

/**
 * Which letters sit where.
 *
 * Sequential, so one hue and lightness carries magnitude — never a rainbow. The
 * scale runs from the page ground to the accent, and the value encoded is the
 * share of words *that reach this position* which have this letter there, not a
 * raw count. Raw counts would draw the same picture for every column: a slope
 * showing that long words are rarer, which is the length chart's job.
 */
export function LetterPosition({ stats }: { stats: Stats }) {
  const [hover, setHover] = useState<{ letter: number; position: number } | null>(null);

  const { counts, columnTotals, positions } = stats.letterPosition;

  const shares = counts.map((row) =>
    row.map((count, p) => (columnTotals[p]! === 0 ? 0 : count / columnTotals[p]!)),
  );
  const maxShare = Math.max(...shares.flat());

  const W = LABEL_W + positions * (CELL + GAP);
  const H = HEADER_H + 26 * (CELL + GAP);

  const active = hover ? { ...hover, share: shares[hover.letter]![hover.position]! } : null;

  // Per column, which letter leads — the direct labels that keep this readable
  // without decoding colour.
  const leaders = Array.from({ length: positions }, (_, p) => {
    let best = 0;
    for (let l = 1; l < 26; l++) if (shares[l]![p]! > shares[best]![p]!) best = l;
    return best;
  });

  return (
    <Figure
      title="Which letters sit where"
      lede={`Share of words reaching each position that carry a given letter there. Position 1 belongs to consonants — ${LETTERS[leaders[0]!]} leads. Position 2 is overwhelmingly a vowel. By position 10 the list is reading suffixes, and ${LETTERS[leaders[9]!]} takes over.`}
      note={
        <>
          Only the first {positions} positions, and only <code className="font-mono text-xs">a–z</code>{' '}
          bytes. The denominator for each column is the number of words at least that long, so a
          share is never above 100%.
        </>
      }
      table={{
        columns: ['Letter', ...Array.from({ length: positions }, (_, p) => `${p + 1}`)],
        rows: LETTERS.map((letter, li) => [
          letter,
          ...shares[li]!.map((s) => `${(s * 100).toFixed(1)}%`),
        ]),
      }}
    >
      <Readout>
        {active ? (
          <>
            <span className="text-ink">
              {LETTERS[active.letter]} at position {active.position + 1}
            </span>
            <span>
              {(active.share * 100).toFixed(1)}% of the{' '}
              {n(columnTotals[active.position]!)} words that reach it ·{' '}
              {n(counts[active.letter]![active.position]!)} words
            </span>
          </>
        ) : (
          <span className="text-ink-faint">Hover a cell for its share</span>
        )}
      </Readout>

      <div className="overflow-x-auto">
        {/* Explicit width with `height: auto`, never `w-full`. This grid is
            taller than it is wide (358 × 746), so stretching it to the column
            width scaled it past 2,000px of vertical space — a cell is meant to
            be a small square, not a tile. It shrinks on narrow screens and the
            wrapper scrolls sideways below its natural size. */}
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width={W}
          height={H}
          className="mt-1"
          role="img"
          aria-label="Heatmap of letter frequency by position within the word."
          onPointerLeave={() => setHover(null)}
        >
          {Array.from({ length: positions }, (_, p) => (
            <text
              key={p}
              x={LABEL_W + p * (CELL + GAP) + CELL / 2}
              y={11}
              textAnchor="middle"
              className="fill-ink-faint font-mono"
              fontSize="9"
            >
              {p + 1}
            </text>
          ))}

          {LETTERS.map((letter, li) => (
            <text
              key={letter}
              x={LABEL_W - 6}
              y={HEADER_H + li * (CELL + GAP) + CELL / 2 + 3.5}
              textAnchor="end"
              className="fill-ink-faint font-mono"
              fontSize="10"
            >
              {letter}
            </text>
          ))}

          {shares.map((row, li) =>
            row.map((share, p) => {
              const on = hover?.letter === li && hover?.position === p;
              const lead = leaders[p] === li;
              return (
                <g key={`${li}-${p}`}>
                  <rect
                    x={LABEL_W + p * (CELL + GAP)}
                    y={HEADER_H + li * (CELL + GAP)}
                    width={CELL}
                    height={CELL}
                    rx="1"
                    fill="var(--color-accent)"
                    fillOpacity={Math.max(0.03, share / maxShare)}
                    stroke={on ? 'var(--color-ink)' : lead ? 'var(--color-accent)' : 'none'}
                    strokeWidth={on ? 1.5 : 1}
                    onPointerEnter={() => setHover({ letter: li, position: p })}
                  />
                  {lead && (
                    <text
                      x={LABEL_W + p * (CELL + GAP) + CELL / 2}
                      y={HEADER_H + li * (CELL + GAP) + CELL / 2 + 3}
                      textAnchor="middle"
                      className="pointer-events-none fill-surface font-mono"
                      fontSize="9"
                    >
                      {letter(li)}
                    </text>
                  )}
                </g>
              );
            }),
          )}
        </svg>
      </div>
    </Figure>
  );
}

function letter(index: number): string {
  return LETTERS[index]!;
}
