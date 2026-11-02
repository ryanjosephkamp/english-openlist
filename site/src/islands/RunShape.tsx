import ChartFrame from '../charts/ChartFrame';
import Columns from '../charts/Columns';
import { plural } from '../charts/format';
import '../charts/charts.css';

interface Props {
  readonly total: number;
  readonly lengths: readonly { length: number; count: number }[];
  readonly firstLetters: readonly { letter: string; count: number }[];
  /** the lengths and first letters of the run's own words, drawn in red */
  readonly addedLengths: readonly number[];
  readonly addedLetters: readonly string[];
}

/** The whole list's shape after 1 run, with the columns its words joined in red. */
export default function RunShape({ total, lengths, firstLetters, addedLengths, addedLetters }: Props) {
  const byLength = new Map(lengths.map((l) => [l.length, l.count]));
  const max = Math.max(...lengths.map((l) => l.length));
  const all = Array.from({ length: max }, (_, i) => ({ length: i + 1, count: byLength.get(i + 1) ?? 0 }));
  const marked = addedLengths.length > 0 || addedLetters.length > 0;
  return (
    <div className="chart-grid">
      <ChartFrame
        title="Length"
        note={marked ? 'The lengths of the words this run added are in red.' : undefined}
        table={all.map((l) => ({ label: plural(l.length, 'letter'), value: l.count }))}
        total={total}
      >
        <Columns
          label="Words by length in letters, after this run"
          columns={all.map((l) => ({ key: String(l.length), label: String(l.length), name: plural(l.length, 'letter'), value: l.count }))}
          total={total}
          labelEvery={5}
          selected={marked ? (i) => addedLengths.includes(i + 1) : undefined}
        />
      </ChartFrame>
      <ChartFrame
        title="First letter"
        note={marked ? 'The first letters of the words this run added are in red.' : undefined}
        table={firstLetters.map((l) => ({ label: l.letter, value: l.count }))}
        total={total}
      >
        <Columns
          label="Words by first letter, after this run"
          columns={firstLetters.map((l) => ({ key: l.letter, label: l.letter, name: `Starting with ${l.letter}`, value: l.count }))}
          total={total}
          selected={marked ? (i) => addedLetters.includes(firstLetters[i]!.letter) : undefined}
        />
      </ChartFrame>
    </div>
  );
}
