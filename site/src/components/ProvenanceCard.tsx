import type { Manifest } from '../worker/protocol.ts';
import type { Provenance } from '../state/useProvenance.ts';

const SOURCE_LABEL: Record<string, string> = {
  google_ngrams: 'Google Books Ngrams',
  wiktionary: 'Wiktionary',
  wikipedia: 'Wikipedia',
  opensource: 'Open-source corpora',
  linux: 'Linux word list',
  nltk: 'NLTK',
  coca_frequency: 'COCA frequency list',
  libreoffice: 'LibreOffice dictionary',
  wordnet: 'WordNet',
  enable: 'ENABLE word list',
  collins: 'Collins dictionary',
};

const label = (name: string) => SOURCE_LABEL[name] ?? name.replace(/_/g, ' ');

function Row({ term, children }: { term: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 border-b border-rule px-4 py-3 last:border-b-0 sm:grid-cols-[11rem_1fr] sm:gap-4">
      <dt className="label sm:pt-0.5">{term}</dt>
      <dd className="text-sm text-ink-soft">{children}</dd>
    </div>
  );
}

function Sources({
  names,
  tone,
}: {
  names: readonly string[];
  tone: 'attested' | 'unlikely';
}) {
  return (
    <ul className="flex flex-wrap gap-1.5">
      {names.map((name) => (
        <li
          key={name}
          className={`rounded-[3px] border px-2 py-0.5 text-[12px] ${
            tone === 'attested'
              ? 'border-rule-strong bg-surface text-ink'
              : 'border-rule bg-sunken text-ink-faint'
          }`}
        >
          {label(name)}
        </li>
      ))}
    </ul>
  );
}

export function ProvenanceCard({
  provenance,
  manifest,
}: {
  provenance: Provenance;
  manifest: Manifest;
}) {
  const tables = manifest.provenance;
  const attested = (provenance.a ?? []).map((i) => tables.sources[i] ?? '?');
  const unlikely = (provenance.u ?? []).map((i) => tables.sources[i] ?? '?');

  const manual = provenance.m;
  const manualSource = manual ? (tables.manualSources[manual[0]] ?? '?') : null;
  const manualLlm = manual && manual[1] >= 0 ? (tables.llms[manual[1]] ?? null) : null;
  const manualStatus = manual ? (tables.statuses[manual[3]] ?? 'unknown') : null;

  const category = provenance.g !== undefined ? (tables.categories[provenance.g] ?? null) : null;

  const nothing =
    attested.length === 0 &&
    unlikely.length === 0 &&
    !manual &&
    provenance.c === undefined &&
    provenance.s === undefined &&
    provenance.p === undefined &&
    !category;

  return (
    <section className="flex flex-col gap-3">
      <h2 className="font-display text-xl tracking-tight">How this word was validated</h2>

      {provenance.def && (
        <div className="rounded-[3px] border border-rule bg-surface p-4">
          <div className="flex flex-wrap items-baseline gap-2">
            {provenance.pos && <span className="font-display text-sm italic text-ink-faint">{provenance.pos}</span>}
            {provenance.pron && (
              <span className="font-mono text-[12px] text-ink-faint">{provenance.pron}</span>
            )}
          </div>
          <p className="mt-1 font-display text-lg text-ink">{provenance.def}</p>
          <p className="mt-2 text-sm text-ink-faint">
            One of only {manifest.provenance.withDefinition} entries in the dataset carrying a
            definition. The other {(manifest.wordCount - manifest.provenance.withDefinition).toLocaleString()} record
            only how they were validated — this list is a record of word <em>validity</em>, not a
            dictionary of meanings.
          </p>
        </div>
      )}

      {nothing ? (
        <p className="max-w-[62ch] text-sm text-ink-soft">
          This entry records nothing beyond the intake it arrived through. That is the ordinary case
          for the tournament word list: its whole claim is that the tournament list contains the
          word.
        </p>
      ) : (
        <dl className="rounded-[3px] border border-rule bg-surface">
          {attested.length > 0 && (
            <Row term={`Attested by ${attested.length}`}>
              <Sources names={attested} tone="attested" />
            </Row>
          )}

          {unlikely.length > 0 && (
            <Row term={`Called unlikely by ${unlikely.length}`}>
              <Sources names={unlikely} tone="unlikely" />
              {attested.length === 0 && (
                <p className="mt-2 text-ink-faint">
                  Every source that looked at this word doubted it, and it is on the valid list
                  anyway. Worth knowing before you rely on it.
                </p>
              )}
            </Row>
          )}

          {category && <Row term="Generated category">{category}</Row>}

          {manual && (
            <Row term="Checked by a model">
              <span className="text-ink">{manualLlm ?? 'an unnamed model'}</span>
              {manualStatus !== 'unknown' && <> · found it {manualStatus}</>}
              <br />
              <span className="font-mono text-[12px] text-ink-faint">
                {manualSource?.replace(/_/g, ' ')}
                {manual[2] && ` · ${manual[2]}`}
              </span>
            </Row>
          )}

          {(provenance.c !== undefined || provenance.s !== undefined) && (
            <Row term="Automated checks">
              <span className="font-mono text-[13px]">
                {provenance.c !== undefined && <>pattern {provenance.c}%</>}
                {provenance.c !== undefined && provenance.s !== undefined && ' · '}
                {provenance.s !== undefined && <>statistical {provenance.s}%</>}
              </span>
            </Row>
          )}

          {provenance.p !== undefined && (
            <Row term="Proper noun">
              {provenance.p === 2 ? 'Flagged as a proper noun' : 'Checked, and not a proper noun'}
            </Row>
          )}

          {provenance.d && <Row term="Validated">{provenance.d}</Row>}
        </dl>
      )}
    </section>
  );
}
