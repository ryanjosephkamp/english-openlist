import { useEffect, useState } from 'react';
import { WordFlag } from '@eol/wordlist/format';
import type { Row } from '../worker/protocol.ts';
import type { useSearch } from '../state/useSearch.ts';
import { INTAKE_NOTE, intakeLabel, intakeName } from '../util/format.ts';
import { useProvenance } from '../state/useProvenance.ts';
import { ProvenanceCard } from '../components/ProvenanceCard.tsx';

const INTAKE_DOT: Record<string, string> = {
  twl: 'bg-intake-twl',
  pipeline: 'bg-intake-pipeline',
  synthetic: 'bg-intake-synthetic',
  other: 'bg-intake-other',
};

export function WordPage({ word, search }: { word: string; search: ReturnType<typeof useSearch> }) {
  const [row, setRow] = useState<Row | null | undefined>(undefined);
  // Requested as soon as the word is known rather than after the lookup
  // resolves: the shard is ~6.4 KB and the two round trips overlap.
  const provenance = useProvenance(row === null ? null : word, search.manifest?.provenance.shards);

  useEffect(() => {
    if (search.status !== 'ready') return;
    let live = true;
    void search.lookup(word).then((found) => {
      if (live) setRow(found);
    });
    return () => {
      live = false;
    };
  }, [word, search]);

  if (row === undefined) {
    return <p className="py-16 text-center text-ink-faint">Looking up “{word}”…</p>;
  }

  if (row === null) {
    return (
      <div className="py-16">
        <h1 className="font-display text-4xl tracking-tight">{word}</h1>
        <p className="mt-3 max-w-[62ch] text-ink-soft">
          Not in the valid list. That is not a claim it is not a word — it means no source in this
          dataset has attested it. It may well be among the 9.28 million entries on the invalid list,
          which is where the daily pipeline goes looking.
        </p>
        <a
          href="/"
          className="mt-6 inline-block text-sm text-ink-soft underline decoration-rule-strong underline-offset-4 transition-colors duration-150 hover:text-accent hover:decoration-accent"
        >
          Back to the list
        </a>
      </div>
    );
  }

  const name = intakeName(row.intake);
  const contested = (row.flags & WordFlag.LlmSaysInvalid) !== 0;
  const alsoInvalid = (row.flags & WordFlag.AlsoInvalid) !== 0;

  return (
    <article className="flex flex-col gap-8 py-6">
      <header className="flex flex-col gap-2">
        <h1 className="font-display text-5xl tracking-tight">{row.word}</h1>
        <p className="font-mono text-xs text-ink-faint">
          {row.word.length} letters · index {row.index.toLocaleString()} in the sorted list
        </p>
      </header>

      <dl className="grid gap-px border border-rule bg-rule sm:grid-cols-2">
        <div className="bg-surface p-4">
          <dt className="label">Intake</dt>
          <dd className="mt-1 flex items-baseline gap-2">
            <span
              aria-hidden
              className={`inline-block h-2 w-2 shrink-0 translate-y-[-1px] rounded-full ${INTAKE_DOT[name]}`}
            />
            <span className="text-ink">{intakeLabel(row.intake)}</span>
          </dd>
          <dd className="mt-1 text-sm text-ink-soft">{INTAKE_NOTE[name]}</dd>
        </div>

        <div className="bg-surface p-4">
          <dt className="label">Recorded</dt>
          <dd className="mt-1 font-mono text-ink">{row.added || 'no date recorded'}</dd>
          <dd className="mt-1 text-sm text-ink-soft">
            {row.added === '2025-12-17' || row.added === '2026-01-10' || row.added === '2026-01-11'
              ? 'A bulk-load date — the day this whole intake landed, not the day this word was found.'
              : row.added
                ? 'Added on its own, after the founding intakes.'
                : 'This entry predates the pipeline recording dates.'}
          </dd>
        </div>
      </dl>

      {(contested || alsoInvalid) && (
        <div className="rounded-[3px] border border-accent bg-accent-wash p-4">
          <h2 className="label text-accent">Worth knowing</h2>
          <ul className="mt-2 flex flex-col gap-1 text-sm text-ink-soft">
            {contested && (
              <li>
                One LLM pass, in December 2025, called this word invalid — recorded as{' '}
                <code className="font-mono text-xs">unverified_llm_verdict</code>. It is an
                opinion, not a ruling, and 20,052 entries carry one. Where a real dictionary
                could check that pass, it was <a href="/as-it-is">wrong more often than right</a>,
                so no word was moved because of it.
              </li>
            )}
            {alsoInvalid && (
              <li>
                This word also appears in the invalid list. 150 words appear in both, all of them
                recent additions never removed from the other side.
              </li>
            )}
          </ul>
        </div>
      )}

      {provenance.status === 'ready' && provenance.provenance && search.manifest && (
        <ProvenanceCard provenance={provenance.provenance} manifest={search.manifest} />
      )}

      {provenance.status === 'failed' && (
        <p className="text-sm text-ink-faint">
          The validation record could not be loaded ({provenance.message}). Everything above comes
          from the word list itself and is unaffected.
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <a
          href={`https://ars-magna.pages.dev/#q=${encodeURIComponent(row.word)}`}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-[3px] border border-rule bg-surface px-3 py-1.5 text-sm text-ink-soft transition-colors duration-150 hover:border-accent hover:bg-accent-wash hover:text-accent"
        >
          Anagrams of this word →
        </a>
        <a
          href={`/?q=${encodeURIComponent(row.word)}&m=contains`}
          className="rounded-[3px] border border-rule bg-surface px-3 py-1.5 text-sm text-ink-soft transition-colors duration-150 hover:border-accent hover:bg-accent-wash hover:text-accent"
        >
          Words containing it
        </a>
      </div>
    </article>
  );
}
