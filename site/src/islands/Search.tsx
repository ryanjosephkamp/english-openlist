import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { DEFAULT_QUERY, LISTED_BY, type EngineFilter, type ListedBy, type MatchMode, type Query, type SortKey } from '@eol/wordlist/query';
import { WordFlag } from '@eol/wordlist/format';
import { ENGINE_WHAT, joinNames, listedByLabel, listedLabels, listedShort, listedState, listedTone, LISTED_WHAT } from '../util/listed';
import { useSearch } from './useSearch';
import { paramsToQuery, queryToUrl } from './urlState';
import WordPanel from './WordPanel';
import type { ExportFormat, Row } from '../worker/protocol';
import { plural } from '../charts/format';
import '../charts/charts.css';
import './search.css';

/** Rows shown at first, and added by each press of Show more. */
const STEP = 100;
const LETTERS = 'abcdefghijklmnopqrstuvwxyz'.split('');

const MODES: readonly { mode: MatchMode; label: string; placeholder: string }[] = [
  { mode: 'prefix', label: 'Starts with', placeholder: 'Type the start of a word' },
  { mode: 'contains', label: 'Contains', placeholder: 'Type letters the word contains' },
  { mode: 'suffix', label: 'Ends with', placeholder: 'Type the end of a word' },
  { mode: 'pattern', label: 'Pattern', placeholder: '_ is 1 letter, * is any run: st__m*' },
  { mode: 'regex', label: 'Regular expression', placeholder: 'A JavaScript regular expression' },
];

const SORTS: readonly { sort: SortKey; label: string }[] = [
  { sort: 'alpha', label: 'A to Z' },
  { sort: 'length', label: 'Length' },
  { sort: 'added', label: 'Date added' },
];

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function shortDate(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  return m ? `${MONTHS[Number(m[2]) - 1]} ${Number(m[3])}, ${m[1]}` : '';
}

const full = (n: number) => n.toLocaleString('en-US');

const ENGINE_OPTIONS: readonly { value: EngineFilter; label: string }[] = [
  { value: 'any', label: 'Any word' },
  { value: 'only', label: 'Only the words it made' },
  { value: 'without', label: 'Leave out the words it made' },
];

interface Props {
  /** each listed-by value's count in the whole list, for the filter's labels */
  readonly listedCounts: Readonly<Record<ListedBy, number>>;
  /** the words the synthetic engine made, in the whole list */
  readonly engineCount: number;
  readonly maxLength: number;
  /** words to start from, each from the vetted example list */
  readonly examples: readonly string[];
  /** every day a nightly run has a page in the daily log */
  readonly runDates: readonly string[];
  /** days that date more words than a night's run adds, with their counts */
  readonly bulkDates: readonly { date: string; count: number }[];
}

/** The URL with the open word's panel, or without it. */
function withWord(url: string, word: string | null): string {
  const [path, search = ''] = url.split('?');
  const params = new URLSearchParams(search);
  if (word) params.set('w', word);
  else params.delete('w');
  const query = params.toString().replace(/\+/g, '%20');
  return query ? `${path}?${query}` : path!;
}

/** Search and filter the whole list, in the browser. */
export default function Search({ listedCounts, engineCount, maxLength, examples, runDates, bulkDates }: Props) {
  const [query, setQuery] = useState<Query>(DEFAULT_QUERY);
  const [ready, setReady] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [shown, setShown] = useState(STEP);
  /** the word whose panel is open, with its row once looked up */
  const [panel, setPanel] = useState<{ word: string; row: Row | null | undefined } | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [exporting, setExporting] = useState<ExportFormat | null>(null);
  const runSet = useMemo(() => new Set(runDates), [runDates]);
  const bulkMap = useMemo(() => new Map(bulkDates.map((b) => [b.date, b.count])), [bulkDates]);

  // The query and the open word come from the URL once, after the first
  // paint, and go back to it on every change, so a search or a word is a link.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setQuery(paramsToQuery(params));
    const w = params.get('w');
    if (w) setPanel({ word: w.trim().toLowerCase(), row: undefined });
    setReady(true);
    // Back closes a panel opened here; forward opens it again.
    const pop = () => {
      const again = new URLSearchParams(window.location.search).get('w');
      setPanel(again ? { word: again, row: undefined } : null);
    };
    window.addEventListener('popstate', pop);
    return () => window.removeEventListener('popstate', pop);
  }, []);
  useEffect(() => {
    if (!ready) return;
    const url = withWord(queryToUrl(window.location.pathname, query), new URLSearchParams(window.location.search).get('w'));
    if (url !== window.location.pathname + window.location.search) history.replaceState(history.state, '', url);
  }, [query, ready]);
  // A new search starts from its first rows.
  useEffect(() => setShown(STEP), [query]);
  useEffect(() => {
    if (!copied) return;
    const t = setTimeout(() => setCopied(null), 2000);
    return () => clearTimeout(t);
  }, [copied]);

  const search = useSearch(query);
  const set = (patch: Partial<Query>) => setQuery((q) => ({ ...q, ...patch }));

  // A panel opened from a link looks its word up once the list is in.
  const { lookup } = search;
  useEffect(() => {
    if (!panel || panel.row !== undefined || search.status !== 'ready') return;
    let live = true;
    void lookup(panel.word).then((row) => live && setPanel((p) => (p && p.word === panel.word ? { ...p, row } : p)));
    return () => {
      live = false;
    };
  }, [panel, search.status, lookup]);

  const openWord = useCallback((row: Row) => {
    setPanel({ word: row.word, row });
    const url = withWord(window.location.pathname + window.location.search, row.word);
    history.pushState({ eolPanel: true }, '', url);
  }, []);
  const closeWord = useCallback(() => {
    setPanel(null);
    if ((history.state as { eolPanel?: boolean } | null)?.eolPanel) history.back();
    else history.replaceState(null, '', withWord(window.location.pathname + window.location.search, null));
  }, []);
  const searchFrom = (word: string) => {
    setPanel(null);
    history.replaceState(null, '', withWord(window.location.pathname + window.location.search, null));
    setQuery({ ...DEFAULT_QUERY, text: word, mode: 'prefix' });
  };

  const surprise = async () => {
    if (search.count === 0) return;
    const row = await search.pick(Math.floor(Math.random() * search.count));
    if (row) openWord(row);
  };
  const copyLink = () => {
    navigator.clipboard
      ?.writeText(window.location.href)
      .then(() => setCopied('link'))
      .catch(() => setCopied('failed'));
  };
  const download = async (format: ExportFormat) => {
    setExporting(format);
    try {
      const text = await search.exportAs(format);
      const blob = new Blob([text], { type: format === 'csv' ? 'text/csv' : 'text/plain' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `english-openlist-${search.count}-${search.count === 1 ? 'word' : 'words'}.${format}`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 10_000);
    } finally {
      setExporting(null);
    }
  };
  const mode = MODES.find((m) => m.mode === query.mode) ?? MODES[0]!;
  const filtered =
    query.listedBy.length > 0 ||
    query.engine !== DEFAULT_QUERY.engine ||
    query.letters.length > 0 ||
    query.minLength !== DEFAULT_QUERY.minLength ||
    query.maxLength !== DEFAULT_QUERY.maxLength;
  const toggle = <T,>(list: readonly T[], item: T): T[] =>
    list.includes(item) ? list.filter((x) => x !== item) : [...list, item];

  return (
    <div className="find">
      <div className="search">
        <label className="search-label" htmlFor="q">
          Search the list
        </label>
        <div className="search-row">
          <input
            id="q"
            type="search"
            inputMode="search"
            autoComplete="off"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            placeholder={mode.placeholder}
            value={query.text}
            onChange={(e) => set({ text: e.target.value })}
            aria-describedby="q-count"
          />
        </div>
        <fieldset className="modes">
          <legend className="visually-hidden">How the text matches</legend>
          {MODES.map((m) => (
            <label key={m.mode} className={query.mode === m.mode ? 'on' : undefined}>
              <input
                type="radio"
                name="mode"
                value={m.mode}
                checked={query.mode === m.mode}
                onChange={() => set({ mode: m.mode })}
              />
              {m.label}
            </label>
          ))}
        </fieldset>
      </div>

      <div className="find-body">
        <aside aria-label="Filters">
          <button
            type="button"
            className="facets-toggle"
            aria-expanded={filtersOpen}
            aria-controls="facets"
            onClick={() => setFiltersOpen((o) => !o)}
          >
            {filtersOpen ? 'Hide the filters' : 'Filters'}
            {filtered && <span className="facets-on">on</span>}
          </button>
          <div id="facets" className={`facets${filtersOpen ? ' is-open' : ''}`}>
            <Group legend="Length" hint={`1 to ${maxLength} letters`}>
              <div className="range">
                <label>
                  At least
                  <input
                    type="number"
                    min={1}
                    max={maxLength}
                    value={query.minLength}
                    onChange={(e) => set({ minLength: bound(e.target.value, 1, maxLength, 1) })}
                  />
                </label>
                <label>
                  At most
                  <input
                    type="number"
                    min={1}
                    max={maxLength}
                    value={Math.min(query.maxLength, maxLength)}
                    onChange={(e) => {
                      const n = bound(e.target.value, 1, maxLength, maxLength);
                      set({ maxLength: n >= maxLength ? DEFAULT_QUERY.maxLength : n });
                    }}
                  />
                </label>
              </div>
            </Group>

            <Group legend="Listed by" hint="Any, unless you choose; a word matches any you choose">
              {LISTED_BY.map((value) => (
                <label key={value} className={`opt${listedCounts[value] === 0 ? ' none' : ''}`}>
                  <input
                    type="checkbox"
                    checked={query.listedBy.includes(value)}
                    onChange={() => set({ listedBy: LISTED_BY.filter((v) => (v === value) !== query.listedBy.includes(v)) })}
                  />
                  <span className="opt-label">{listedByLabel(value)}</span>
                  <span className="opt-n">{full(listedCounts[value])}</span>
                </label>
              ))}
            </Group>

            <Group legend="Synthetic engine" hint={`${full(engineCount)} words, made by rule`}>
              {ENGINE_OPTIONS.map((o) => (
                <label key={o.value} className="opt">
                  <input
                    type="radio"
                    name="engine"
                    value={o.value}
                    checked={query.engine === o.value}
                    onChange={() => set({ engine: o.value })}
                  />
                  <span className="opt-label">{o.label}</span>
                </label>
              ))}
            </Group>

            <Group legend="First letter" hint="Any, unless you choose">
              <div className="letters">
                {LETTERS.map((l) => (
                  <button
                    key={l}
                    type="button"
                    aria-pressed={query.letters.includes(l)}
                    onClick={() => set({ letters: toggle(query.letters, l).sort() })}
                  >
                    {l}
                  </button>
                ))}
              </div>
            </Group>

            <Group legend="Order">
              <div className="sorts">
                <select
                  aria-label="Sort by"
                  value={query.sort}
                  onChange={(e) => set({ sort: e.target.value as SortKey })}
                >
                  {SORTS.map((s) => (
                    <option key={s.sort} value={s.sort}>
                      {s.label}
                    </option>
                  ))}
                </select>
                <label className="opt">
                  <input
                    type="checkbox"
                    checked={query.descending}
                    onChange={(e) => set({ descending: e.target.checked })}
                  />
                  <span className="opt-label">Reversed</span>
                </label>
              </div>
            </Group>

            {(filtered || query.text) && (
              <button type="button" className="clear" onClick={() => setQuery(DEFAULT_QUERY)}>
                Clear the search
              </button>
            )}
          </div>
        </aside>

        <section className="results" aria-label="Results">
          <div className="results-head">
            <Count search={search} text={query.text} />
            {search.status === 'ready' && search.count > 0 && (
              <div className="tools">
                <button type="button" onClick={() => void surprise()}>
                  Surprise me
                </button>
                <button type="button" onClick={copyLink}>
                  {copied === 'link' ? 'Copied' : copied === 'failed' ? 'Could not copy' : 'Copy link'}
                </button>
                <span className="tools-export" role="group" aria-label="Download these words">
                  <span className="tools-label">Download</span>
                  {(['txt', 'csv'] as const).map((f) => (
                    <button
                      key={f}
                      type="button"
                      disabled={exporting !== null}
                      onClick={() => void download(f)}
                      aria-label={`Download ${search.count === 1 ? 'this word' : `these ${full(search.count)} words`} as ${f.toUpperCase()}`}
                    >
                      {exporting === f ? '…' : f.toUpperCase()}
                    </button>
                  ))}
                </span>
              </div>
            )}
          </div>
          {search.status === 'ready' && !query.text && !filtered && (
            <div className="start-from">
              <p>Every word of the list is here, in your browser. Type to search, or start from one:</p>
              <ul>
                {examples.map((w) => (
                  <li key={w}>
                    <button type="button" className="word" onClick={() => set({ text: w, mode: 'prefix' })}>
                      {w}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {search.status === 'ready' && search.count === 0 && !search.error && (
            <div className="empty">
              <p>Nothing matches {query.text ? <span className="word">“{query.text}”</span> : 'these filters'}.</p>
              <p>The list holds lowercase a to z only, so a capital, a space, or a hyphen never matches.</p>
            </div>
          )}
          {search.status === 'ready' && search.count > 0 && (
            <>
              <Rows count={Math.min(shown, search.count)} rowAt={search.rowAt} onOpen={openWord} />
              <div className="more">
                <p>
                  Showing {search.count <= shown ? (search.count === 1 ? 'the only match' : `all ${full(search.count)}`) : `1 to ${full(shown)} of ${full(search.count)}`}.
                  {search.count > shown && ' Select a word for its entry.'}
                </p>
                {search.count > shown && (
                  <button type="button" onClick={() => setShown((n) => n + STEP)}>
                    Show {full(Math.min(STEP, search.count - shown))} more
                  </button>
                )}
              </div>
            </>
          )}
        </section>
      </div>

      {panel && (
        <WordPanel
          key={panel.word}
          word={panel.word}
          row={panel.row}
          runDates={runSet}
          bulkDates={bulkMap}
          onClose={closeWord}
          onSearch={searchFrom}
        />
      )}
    </div>
  );
}

function Count({ search, text }: { search: ReturnType<typeof useSearch>; text: string }) {
  let body: ReactNode;
  if (search.status === 'loading') body = 'Loading the list…';
  else if (search.status === 'failed') body = `The list did not load (${search.failure}). Reload the page to try again.`;
  else if (search.error) body = `That is not a regular expression this browser can read: ${search.error}`;
  else
    body = (
      <>
        <strong>{full(search.count)}</strong> {search.count === 1 ? 'word' : 'words'}
        {text || search.count !== search.manifest?.wordCount ? ' match' : ' in the list'}
        <span className="count-time">
          {' '}
          · {search.millis < 1 ? 'under 1' : Math.round(search.millis)} ms
        </span>
      </>
    );
  return (
    <p id="q-count" className="count" aria-live="polite" aria-busy={search.searching}>
      {body}
    </p>
  );
}

interface RowsProps {
  readonly count: number;
  readonly rowAt: ReturnType<typeof useSearch>['rowAt'];
  readonly onOpen: (row: Row) => void;
}

/** What a row's listed-by chip says on hover. */
function listedTitle(attested: number): string {
  const state = listedState(attested);
  return state === 'listed' ? `Listed by ${joinNames(listedLabels(attested))}` : LISTED_WHAT[state];
}

/** The rows shown so far, numbered; each opens its word's panel. */
function Rows({ count, rowAt, onOpen }: RowsProps) {
  return (
    <ol className="rows" aria-label="Matching words" style={{ ['--nw' as string]: `${String(count).length + 1}ch` }}>
      {Array.from({ length: count }, (_, i) => {
        const row = rowAt(i);
        return (
          <li key={i} className="row">
            {row ? (
              <button type="button" className="row-hit" onClick={() => onOpen(row)}>
                <span className="row-n">{full(i + 1)}</span>
                <span className="row-word word">{row.word}</span>
                <span className="row-meta">
                  <span>{plural(row.word.length, 'letter')}</span>
                  <span className={`listed ${listedTone(row.attested)}`} title={listedTitle(row.attested)}>
                    {listedShort(row.attested)}
                  </span>
                  {row.added && <span className="row-date">added {shortDate(row.added)}</span>}
                  {(row.flags & WordFlag.Engine) !== 0 && (
                    <span className="flag" title={ENGINE_WHAT}>
                      made by the synthetic engine
                    </span>
                  )}
                </span>
              </button>
            ) : (
              <span className="row-hit row-wait-wrap" aria-hidden="true">
                <span className="row-n">{full(i + 1)}</span>
                <span className="row-wait" />
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function Group({ legend, hint, children }: { legend: string; hint?: string; children: ReactNode }) {
  return (
    <fieldset className="group">
      <legend>
        {legend}
        {hint && <span className="hint">{hint}</span>}
      </legend>
      {children}
    </fieldset>
  );
}

function bound(raw: string, lo: number, hi: number, fallback: number): number {
  const n = Number(raw);
  if (!Number.isInteger(n)) return fallback;
  return Math.max(lo, Math.min(hi, n));
}
