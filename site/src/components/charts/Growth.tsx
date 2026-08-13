import type { Stats } from '../../state/useStats.ts';
import { n } from '../../util/format.ts';

/**
 * Deliberately not a chart.
 *
 * Over the 80 days the daily log records a total, the list moved by 8 words on
 * 7 days — 0.0021% of it. On a zero-based axis that is a flat line carrying no
 * information. On an axis zoomed to the data it is a dramatic staircase, which
 * would be a lie told with a y-axis: the reader would take away "this list is
 * growing" when the truth is "this list is essentially fixed, and the daily job
 * is working through 9.3 million rejected entries looking for the occasional
 * survivor".
 *
 * So: the figures, and the seven events that produced them.
 */
export function Growth({ stats }: { stats: Stats }) {
  const g = stats.growth;
  const change = g.last - g.first;
  const share = (change / g.last) * 100;

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <h2 className="font-display text-xl tracking-tight text-ink">How much it changes</h2>
        <p className="max-w-[62ch] text-sm text-ink-soft">
          Almost not at all, and that is the point. This is not a list being grown — it is a list
          being <em>checked</em>. Every night the pipeline validates about a thousand entries from
          the 9,275,411 on the invalid list, and most nights nothing survives.
        </p>
      </div>

      <div className="grid gap-px border border-rule bg-rule sm:grid-cols-3">
        <Stat
          value={`+${change}`}
          label="words"
          note={`across ${g.daysRecorded} recorded days, ${g.recordedFrom} to ${g.recordedTo}`}
        />
        <Stat value={`${share.toFixed(4)}%`} label="of the list" note="the entire recorded change" />
        <Stat
          value={String(g.events.length)}
          label={g.events.length === 1 ? 'day it moved' : 'days it moved'}
          note={`the other ${g.daysRecorded - g.events.length} recorded days were flat`}
        />
      </div>

      <div className="rounded-[3px] border border-rule bg-surface">
        <div className="border-b border-rule px-4 py-2">
          <h3 className="label">Every change in the recorded period</h3>
        </div>
        <ul>
          {g.events.map((event) => (
            <li
              key={event.date}
              className="flex items-baseline justify-between gap-4 border-b border-rule px-4 py-2 last:border-b-0"
            >
              <span className="font-mono text-[13px] text-ink">{event.date}</span>
              <span className="flex items-baseline gap-3 font-mono text-[12px]">
                <span className="text-accent">
                  +{event.delta} {event.delta === 1 ? 'word' : 'words'}
                </span>
                <span className="w-[4.5rem] text-right text-ink-faint tabular-nums">
                  {n(event.total)}
                </span>
              </span>
            </li>
          ))}
        </ul>
      </div>

      {g.daysUnrecorded > 0 && (
        <p className="max-w-[62ch] text-sm text-ink-soft">
          A further {g.daysUnrecorded} days in the log carry{' '}
          <code className="font-mono text-xs">not recorded</code> rather than a total. They are left
          out rather than interpolated — the pipeline's own convention is to say when a metric was
          never captured instead of reconstructing it afterwards.
        </p>
      )}
    </section>
  );
}

function Stat({ value, label, note }: { value: string; label: string; note: string }) {
  return (
    <div className="bg-surface p-4">
      <div className="flex items-baseline gap-2">
        <span className="font-display text-3xl text-accent tabular-nums">{value}</span>
        <span className="text-sm text-ink-soft">{label}</span>
      </div>
      <p className="mt-1 text-sm text-ink-faint">{note}</p>
    </div>
  );
}
