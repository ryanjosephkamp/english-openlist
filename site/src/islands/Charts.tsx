import BarList from '../charts/BarList';
import ChartFrame from '../charts/ChartFrame';
import Columns from '../charts/Columns';
import Growth from '../charts/Growth';
import { full, pct, plural } from '../charts/format';
import type { Stats } from '../util/data';
import '../charts/charts.css';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const longDate = (iso: string) => {
  const [y, m, d] = iso.split('-').map(Number);
  return `${MONTHS[m! - 1]} ${d}, ${y}`;
};
const signed = (n: number) => (n > 0 ? `+${full(n)}` : `−${full(-n)}`);

interface Props {
  readonly stats: Stats;
  /** which chart group this island draws */
  readonly part: 'shape' | 'origin' | 'growth';
}

/** The list's charts, each with a table view of the same figures. */
export default function Charts({ stats, part }: Props) {
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
          table={lengths.map((l) => ({ label: plural(l.length, 'letter'), value: l.count }))}
          total={total}
          valueLabel="Words"
        >
          <Columns
            label="Words by length in letters"
            columns={lengths.map((l) => ({ key: String(l.length), label: String(l.length), name: plural(l.length, 'letter'), value: l.count }))}
            total={total}
            labelEvery={5}
            unit="word"
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
            unit="letter"
          />
        </ChartFrame>
      </div>
    );
  }

  if (part === 'origin') {
    const at = stats.attestation;
    const sourceCount = at.sources.length;
    // Most sources first; a word no source lists, or one not checked yet, is gray.
    const howMany = [
      ...at.bySourceCount
        .map((count, k) => ({
          key: `n${k}`,
          label: k === 0 ? 'None of them' : k === sourceCount ? `All ${sourceCount}` : `${k} of ${sourceCount}`,
          value: count,
          ...(k === 0 ? { tone: 'muted' as const } : {}),
        }))
        .reverse(),
      ...(at.unchecked > 0 ? [{ key: 'unchecked', label: 'Not checked yet', value: at.unchecked, tone: 'muted' as const }] : []),
    ];
    const bySource = at.sources.map((s) => ({ key: s.key, label: s.label, value: s.count }));
    return (
      <div className="chart-grid">
        <ChartFrame
          title="How many open sources list each word"
          note={
            <>
              {full(at.atLeastOne)} words ({pct(at.atLeastOne, total)}) are listed by at least 1 of the {sourceCount} open
              sources, and {full(at.none)} by none of them. That says what those sources hold, not whether a word is English.
            </>
          }
          table={howMany.map((b) => ({ label: b.label, value: b.value }))}
          total={total}
          valueLabel="Words"
        >
          <BarList label="Words by how many open sources list them" bars={howMany} total={total} />
        </ChartFrame>

        <ChartFrame
          title="Words by the open sources that list them"
          note="A word counts once under each source that lists it, so the bars add up to more than the list."
          table={bySource.map((b) => ({ label: b.label, value: b.value }))}
          total={total}
          valueLabel="Words"
        >
          <BarList label="Words by the open sources that list them" bars={bySource} total={total} />
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
    </div>
  );
}
