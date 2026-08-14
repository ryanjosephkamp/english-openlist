import type { Manifest } from '../worker/protocol.ts';
import { n } from '../util/format.ts';

function Item({
  figure,
  title,
  children,
}: {
  figure: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-2 border-t border-rule pt-5">
      <div className="flex flex-wrap items-baseline gap-3">
        <span className="font-display text-2xl text-accent tabular-nums">{figure}</span>
        <h2 className="font-display text-xl tracking-tight text-ink">{title}</h2>
      </div>
      <div className="flex max-w-[64ch] flex-col gap-2 text-ink-soft">{children}</div>
    </section>
  );
}

/**
 * What the dataset actually is, including the parts that are ragged.
 *
 * Every figure comes from the build, not from prose written once and left to
 * rot. If a number here changes, it changes because the dataset changed.
 */
export function AsItIsPage({ manifest }: { manifest: Manifest | null }) {
  if (!manifest) return <p className="py-16 text-center text-ink-faint">Reading the list…</p>;

  const synthetic = manifest.intakeCounts['synthetic'] ?? 0;
  const total = manifest.wordCount;

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-4">
        <h1 className="font-display text-3xl tracking-tight sm:text-4xl">The list as it is</h1>
        <p className="max-w-[64ch] text-ink-soft">
          English OpenList is broad on purpose, and breadth has costs. None of what follows is a
          defect being confessed — it is what a list assembled from several intakes over a year
          actually looks like. You should know all of it before you build on it.
        </p>
      </section>

      <Item figure={n(synthetic)} title="words were constructed by an algorithm">
        <p>
          That is {((synthetic / total) * 100).toFixed(1)}% of the list, identifiable by{' '}
          <code className="font-mono text-xs">source: "synthetic_generation"</code>. They were
          built by affixation and marked <code className="font-mono text-xs">validated: true</code>{' '}
          while carrying no evidence of any kind — their own records say “awaiting validation”.
        </p>
        <p>
          <strong>16,476 of them left this list on 14 August 2026.</strong> They were comparatives
          and superlatives — <code className="font-mono text-xs">abacteremicer</code>,{' '}
          <code className="font-mono text-xs">abambulacralest</code> — and you cannot be{' '}
          <em>more</em> abacteremic. Merriam-Webster was asked about 300 of their stems, not by
          looking up the comparative, which it would never carry, but by reading the inflections it
          records for each stem. It could rule on 183, and listed the comparative for exactly one:{' '}
          <a href="/word/blameworthy">blameworthy</a>. That one stayed.
        </p>
        <p>
          They were moved to the invalid list, not deleted, and{' '}
          <strong>every one is queued to be asked about again</strong>. The nightly run reserves
          part of each night for them and skips the filter that would otherwise hide the longer
          ones. A demotion here means no dictionary we could reach knew the word that day — not
          that it is not a word.{' '}
          <a href="https://github.com/ryanjosephkamp/english-openlist/tree/main/corrections">
            Every one names its reason
          </a>
          .
        </p>
        <p>
          The {n(synthetic)} that remain are plurals, past tenses and prefixed forms — unmeasured
          so far, and a mixed bag: <code className="font-mono text-xs">abacavirs</code> is a
          plausible plural of a real drug,{' '}
          <code className="font-mono text-xs">abacaviring</code> is not. They cluster at length —{' '}
          <a href="/shape">the shape page draws it</a>. If you want only words a human source
          attested, that is <a href="/use">one filter or one prebuilt download</a>.
        </p>
      </Item>

      <Item figure={n(manifest.llmSaysInvalid)} title="entries an LLM called invalid">
        <p>
          They carry <code className="font-mono text-xs">unverified_llm_verdict: "invalid"</code>{' '}
          while appearing in the valid word list. Until August 2026 that field was called{' '}
          <code className="font-mono text-xs">status</code>, which made a single machine opinion
          read like the dataset’s own ruling. It never was one.
        </p>
        <p>
          All 20,052 come from one pass by Google Gemini 3 Flash Preview in December 2025 — the
          same pass that marked 117,653 other words valid. So it was measured before anyone acted
          on it: 400 were sampled and looked up in Merriam-Webster. Only{' '}
          <strong>18 could be checked at all</strong>, and of those the LLM was{' '}
          <strong>wrong on 13</strong> — among them <a href="/word/clorazepate">clorazepate</a>, a
          benzodiazepine, and <a href="/word/antinociceptive">antinociceptive</a>. The five it got
          right were all proper nouns.
        </p>
        <p>
          The other 382 could not be checked by anybody:{' '}
          <strong>Merriam-Webster has no entry for 95.8% of this vocabulary</strong>, which is
          mostly chemical, medical and taxonomic. That is the real finding, and it cuts both ways
          — the field is not trustworthy, and no amount of dictionary budget could make these
          words adjudicable. So <strong>nothing was moved</strong>, the verdict is kept with its
          provenance, and{' '}
          <a href="/?c=0">you can exclude them from any search</a> if you want to.
        </p>
      </Item>

      {manifest.alsoInvalid === 0 ? (
        <Item figure="150" title="words were on both lists at once, until they weren’t">
          <p>
            Until 13 August 2026, 150 words appeared in{' '}
            <code className="font-mono text-xs">merged_valid_words.txt</code> and in the{' '}
            {n(manifest.invalidCount)}-entry invalid list simultaneously — words the nightly run had
            promoted onto one side without removing them from the other.
          </p>
          <p>
            Every one of them already carried a Merriam-Webster, MW Medical or Free Dictionary
            ruling inside its own record, so all 150 were cleared against that stored evidence and
            none was demoted. The verdicts and the evidence behind each one are in{' '}
            <code className="font-mono text-xs">corrections/ledger_stage1.csv</code>.
          </p>
          <p className="text-sm text-ink-faint">
            The build now asserts this figure is exactly zero rather than merely small. If it ever
            rises again, the promotion path has regressed.
          </p>
        </Item>
      ) : (
        <Item figure={n(manifest.alsoInvalid)} title="words are on both lists at once">
          <p>
            They appear in <code className="font-mono text-xs">merged_valid_words.txt</code> and in
            the {n(manifest.invalidCount)}-entry invalid list simultaneously. This was corrected to
            zero on 13 August 2026, so any word here is a fresh regression in the promotion path
            rather than old residue.
          </p>
          <p className="text-sm text-ink-faint">
            Few enough to name:{' '}
            <span className="font-mono text-[12px]">
              {manifest.alsoInvalidWords.slice(0, 24).join(', ')}
              {manifest.alsoInvalidWords.length > 24 &&
                ` … and ${manifest.alsoInvalidWords.length - 24} more`}
            </span>
          </p>
        </Item>
      )}

      <Item figure="8 of 11" title="sources can all say “unlikely” at once">
        <p>
          Entries from the verification pipeline carry a{' '}
          <code className="font-mono text-xs">candidate_source</code> list, and each name is
          suffixed <code className="font-mono text-xs">_valid</code> or{' '}
          <code className="font-mono text-xs">_unlikely</code>. Counting the length of that list
          tells you nothing: <a href="/word/aalii">aalii</a> carries eight sources and every one of
          them doubted it.
        </p>
        <p>
          Any word page shows the split rather than the total. There are 11 distinct sources, not
          21 — the larger figure counts each name's two suffixes separately.
        </p>
      </Item>

      <Item figure={n(manifest.bulkDates.reduce((s, d) => s + d.count, 0))} title="words share three dates">
        <p>
          The date on an entry is a bulk-load date, not a discovery date.{' '}
          {manifest.bulkDates.map((d, i) => (
            <span key={d.date}>
              {i > 0 && i === manifest.bulkDates.length - 1 ? ' and ' : i > 0 ? ', ' : ''}
              <span className="font-mono text-[13px]">{d.date}</span> holds {n(d.count)}
            </span>
          ))}
          . Only {manifest.addedSingly} words have ever been added one at a time. Sorting by date is
          mostly one enormous tie, and the explorer says so rather than implying a timeline.
        </p>
      </Item>

      <Item figure={n(manifest.nonAlpha)} title="words are not spelled with only a–z">
        <p>
          188 contain a hyphen and 2 carry an accent —{' '}
          <a href="/word/norte%C3%B1o">norteño</a> and <a href="/word/pel%C3%A9an">peléan</a>. Both
          characters are always internal: no word in the list begins with either. If your code
          assumes <code className="font-mono text-xs">[a-z]</code>, take{' '}
          <a href="/use">the strictly-alphabetic download</a> rather than discovering this later.
        </p>
      </Item>

      <Item figure={`${manifest.provenance.withDefinition}`} title="entries carry a definition">
        <p>
          Out of {n(total)}. This dataset records how each word was <em>validated</em>, not what it
          means: no parts of speech, no pronunciations, no etymologies, except for a handful of
          recent Merriam-Webster additions. Pair it with WordNet or Wiktionary if you need meanings
          — <a href="https://ars-magna.pages.dev">Ars Magna</a> does exactly that.
        </p>
      </Item>

      <p className="border-t border-rule pt-6 text-sm text-ink-faint">
        Every figure on this page is computed from the dataset during the build that produced this
        page, at {manifest.builtAt.slice(0, 16).replace('T', ' ')} UTC. None of it is typed by hand.
      </p>
    </div>
  );
}
