import { useStats } from '../state/useStats.ts';
import { Growth } from '../components/charts/Growth.tsx';
import { LengthChart } from '../components/charts/LengthChart.tsx';
import { IntakeByLength } from '../components/charts/IntakeByLength.tsx';
import { LetterPosition } from '../components/charts/LetterPosition.tsx';
import { n } from '../util/format.ts';

export function ShapePage() {
  const { stats, error } = useStats();

  if (error) {
    return (
      <div className="rounded-[3px] border border-accent bg-accent-wash p-5">
        <h1 className="font-display text-xl text-accent">The figures could not be loaded</h1>
        <p className="mt-1 text-sm text-ink-soft">{error}</p>
      </div>
    );
  }

  if (!stats) {
    return <p className="py-16 text-center text-ink-faint">Reading the figures…</p>;
  }

  const total = stats.lengths.reduce((sum, d) => sum + d.count, 0);

  return (
    <div className="flex flex-col gap-14">
      <section className="flex flex-col gap-4">
        <h1 className="font-display text-3xl tracking-tight sm:text-4xl">
          The shape of {n(total)} words
        </h1>
        <p className="max-w-[62ch] text-ink-soft">
          Four things worth knowing before you build on this list. Every figure here is computed
          from the dataset itself on each deploy, and every chart will show you its own numbers as
          a table.
        </p>
      </section>

      <IntakeByLength stats={stats} />
      <LengthChart stats={stats} />
      <LetterPosition stats={stats} />
      <Growth stats={stats} />
    </div>
  );
}
