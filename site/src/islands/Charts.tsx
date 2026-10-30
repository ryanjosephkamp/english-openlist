import BarList from '../charts/BarList';
import ChartFrame from '../charts/ChartFrame';
import Columns from '../charts/Columns';
import Growth from '../charts/Growth';
import { full, pct } from '../charts/format';
import type { DecidedName, Stats } from '../util/data';
import '../charts/charts.css';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const longDate = (iso: string) => {
  const [y, m, d] = iso.split('-').map(Number);
  return `${MONTHS[m! - 1]} ${d}, ${y}`;
};
const signed = (n: number) => (n > 0 ? `+${full(n)}` : `−${full(-n)}`);

interface Props {
  readonly stats: Stats;
  readonly decidedOrder: readonly DecidedName[];
  readonly decidedLabel: Readonly<Record<DecidedName, string>>;
  readonly decidedWhat: Readonly<Record<DecidedName, string>>;
  /** which chart group this island draws */
  readonly part: 'shape' | 'origin' | 'growth';
}

/** The list's charts, each with a table view of the same figures. */
export default function Charts({ stats, decidedOrder, decidedLabel, decidedWhat, part }: Props) {
  const total = stats.words;

  if (part === 'shape') {
    const maxLen = stats.lengths[stats.lengths.length - 1]!.length;
    const byLen = new Map(stats.lengths.map((l) => [l.length, l.count]));
    const lengths = Array.from({ length: maxLen }, (_, i) => ({ length: i + 1, count: byLen.get(i + 1) ?? 0 }));
    return (
      <div className="chart-grid">
        <ChartFrame
          title="Length"
          note={`From 1 letter to ${maxLen}. The list has no length bound.`}
          table={lengths.map((l) => ({ label: `${l.length} ${l.length === 1 ? 'letter' : 'letters'}`, value: l.count }))}
          total={total}
          valueLabel="Words"
        >
          <Columns
            label="Words by length in letters"
            columns={lengths.map((l) => ({ key: String(l.length), label: String(l.length), name: `${l.length} letters`, value: l.count }))}
            total={total}
            labelEvery={5}
            unit="words"
          />
        </ChartFrame>

        <ChartFrame
          title="First letter"
          table={stats.firstLetters.map((l) => ({ label: l.letter, value: l.count }))}
          total={total}
          valueLabel="Words"
        >
          <Columns
            label="Words by first letter"
            columns={stats.firstLetters.map((l) => ({ key: l.letter, label: l.letter, name: `Starting with ${l.letter}`, value: l.count }))}
            total={total}
          />
        </ChartFrame>

        <ChartFrame
          title="Every letter"
          note={`All ${full(stats.letterTotal)} letters of all ${full(total)} words, counted where they stand.`}
          table={stats.letters.map((l) => ({ label: l.letter, value: l.count }))}
          total={stats.letterTotal}
          valueLabel="Letters"
        >
          <Columns
            label="Letters by how often they appear in the list"
            columns={stats.letters.map((l) => ({ key: l.letter, label: l.letter, name: `The letter ${l.letter}`, value: l.count }))}
            total={stats.letterTotal}
            unit="letters"
          />
        </ChartFrame>
      </div>
    );
  }

  if (part === 'origin') {
    const ch = stats.channels;
    const channelBars = ch.published.filter((c) => c.count > 0).map((c) => ({ key: c.key, label: c.label, value: c.count }));
    return (
      <div className="chart-grid">
        <ChartFrame
          title="What decided each word"
          note="Each word's record, sorted by 1 rule into 4 values."
          table={decidedOrder.map((d) => ({ label: decidedLabel[d], value: stats.decided[d] }))}
          total={total}
          valueLabel="Words"
        >
          <BarList
            label="Words by what decided them"
            bars={decidedOrder.map((d) => ({
              key: d,
              label: decidedLabel[d],
              value: stats.decided[d],
              title: decidedWhat[d],
            }))}
            total={total}
          />
        </ChartFrame>

        <ChartFrame
          title="The channels its words came in by"
          note={
            <>
              A word counts once under each channel its record names, so the bars can add up to more than the list. Most
              are the discovery log, where a word was first seen: a record of intake, not evidence that a source lists the
              word. {full(ch.withPublished)} words ({pct(ch.withPublished, total)}) name at least 1 of these channels.
              Channels withheld for license reasons are not shown.
            </>
          }
          table={channelBars.map((b) => ({ label: b.label, value: b.value }))}
          total={total}
          valueLabel="Words"
        >
          <BarList label="Words by the channels their records name" bars={channelBars} total={total} />
        </ChartFrame>
      </div>
    );
  }

  const g = stats.growth;
  const changes = g.events;
  // A change of 100 words or more is a correction or a catch-up, not a night's
  // promotions; 1,000 or more is labeled on the line, and the table lists all.
  const big = changes.filter((e) => Math.abs(e.delta) >= 100);
  const labeled = changes.filter((e) => Math.abs(e.delta) >= 1000);
  const lo = Math.min(...g.points.map((p) => p.total));
  const hi = Math.max(...g.points.map((p) => p.total));
  const floor = Math.floor(lo / 10_000) * 10_000;
  const ceiling = floor + Math.ceil((hi - floor) / 40_000) * 40_000;

  // The nightly's daily additions after the last correction: every recorded
  // day from the day after the last large change, with its net change.
  const lastBig = big.length ? big[big.length - 1]!.date : g.first.date;
  const after = g.points.filter((p) => p.date > lastBig);
  const prev = new Map(g.points.map((p, i) => [p.date, i > 0 ? g.points[i - 1]!.total : p.total]));
  const added = after.map((p) => ({ date: p.date, value: p.total - prev.get(p.date)! }));
  const addedTotal = added.reduce((s, a) => s + a.value, 0);

  return (
    <div className="chart-grid">
      <ChartFrame
        title="The list's size, day by day"
        note={`${g.points.length} recorded days from ${longDate(g.first.date)} to ${longDate(g.last.date)}, from its daily statistics. The table lists every day the size changed.`}
        table={changes.map((e) => ({ label: `${longDate(e.date)} (${signed(e.delta)})`, value: e.total }))}
        valueLabel="Words after the change"
      >
        <Growth
          points={g.points}
          marks={labeled.map((e) => ({ date: e.date, label: signed(e.delta) }))}
          label={`The list's size from ${longDate(g.first.date)} to ${longDate(g.last.date)}`}
          floor={floor}
          ceiling={ceiling}
        />
      </ChartFrame>

      {added.length > 0 && (
        <ChartFrame
          title="What the nightly run added"
          note={`The net change on each recorded day after ${longDate(lastBig)}: ${full(addedTotal)} words in all, the last on ${longDate(
            [...added].reverse().find((a) => a.value > 0)?.date ?? lastBig,
          )}.`}
          table={added.map((a) => ({ label: longDate(a.date), value: a.value }))}
          valueLabel="Words"
        >
          <Columns
            label="Words added on each recorded day"
            columns={added.map((a) => ({ key: a.date, label: `${MONTHS[Number(a.date.slice(5, 7)) - 1]!.slice(0, 3)} ${Number(a.date.slice(8))}`, name: longDate(a.date), value: Math.max(0, a.value) }))}
            total={Math.max(1, addedTotal)}
            labelEvery={7}
            height={150}
          />
        </ChartFrame>
      )}
    </div>
  );
}
