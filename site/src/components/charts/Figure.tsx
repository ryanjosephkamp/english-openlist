import { useId, useState, type ReactNode } from 'react';

/**
 * The frame every chart on this site sits in.
 *
 * The table is not a fallback, it is a peer. Two of the four intake ramp steps
 * sit under 3:1 against the ground, which is legible as a band in a stack and
 * not legible as a lone swatch — so the same figures are always one click away
 * as text, and screen readers get them without the drawing.
 */
export function Figure({
  title,
  lede,
  note,
  table,
  children,
}: {
  title: string;
  lede?: string;
  note?: ReactNode;
  table: { columns: readonly string[]; rows: readonly (readonly (string | number)[])[] };
  children: ReactNode;
}) {
  const [showTable, setShowTable] = useState(false);
  const tableId = useId();

  return (
    <figure className="flex flex-col gap-3">
      <figcaption className="flex flex-col gap-1.5">
        <h2 className="font-display text-xl tracking-tight text-ink">{title}</h2>
        {lede && <p className="max-w-[62ch] text-sm text-ink-soft">{lede}</p>}
      </figcaption>

      <div className="rounded-[3px] border border-rule bg-surface p-4">{children}</div>

      {note && <div className="max-w-[62ch] text-sm text-ink-soft">{note}</div>}

      <div>
        <button
          type="button"
          onClick={() => setShowTable((v) => !v)}
          aria-expanded={showTable}
          aria-controls={tableId}
          className="text-sm text-ink-faint underline decoration-rule-strong underline-offset-4
                     transition-colors duration-150 hover:text-accent hover:decoration-accent"
        >
          {showTable ? 'Hide the figures' : 'Show the figures'}
        </button>
      </div>

      {showTable && (
        <div id={tableId} className="overflow-x-auto rounded-[3px] border border-rule">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="border-b border-rule bg-sunken">
                {table.columns.map((column, i) => (
                  <th
                    key={column}
                    scope="col"
                    className={`px-3 py-2 font-medium text-ink-soft ${i === 0 ? 'text-left' : 'text-right'}`}
                  >
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row) => (
                <tr key={String(row[0])} className="border-b border-rule last:border-b-0">
                  {row.map((cell, i) => (
                    <td
                      key={i}
                      className={`px-3 py-1.5 font-mono text-[12px] tabular-nums ${
                        i === 0 ? 'text-left text-ink' : 'text-right text-ink-soft'
                      }`}
                    >
                      {typeof cell === 'number' ? cell.toLocaleString('en-US') : cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </figure>
  );
}

/**
 * Horizontal scroll for a chart that has a floor below which it stops being a
 * chart.
 *
 * A viewBox'd SVG set to 100% width keeps its aspect ratio, so on a 375px phone
 * the length chart came out 293 × 98 — 47 columns in 98px of height, which is a
 * texture rather than a distribution. Below `minWidth` the reader swipes
 * instead, which is the same trade the tables make.
 */
export function ChartScroll({ minWidth, children }: { minWidth: number; children: ReactNode }) {
  return (
    <div className="-mx-1 overflow-x-auto px-1">
      <div style={{ minWidth: `${minWidth}px` }}>{children}</div>
    </div>
  );
}

/** A hovering readout pinned inside the chart box rather than following the cursor. */
export function Readout({ children }: { children: ReactNode }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none flex min-h-[1.5rem] items-baseline gap-2 font-mono text-[11px] text-ink-soft"
    >
      {children}
    </div>
  );
}

export const INTAKE_FILL: Record<string, string> = {
  twl: 'var(--color-intake-twl)',
  pipeline: 'var(--color-intake-pipeline)',
  synthetic: 'var(--color-intake-synthetic)',
  other: 'var(--color-intake-other)',
};
