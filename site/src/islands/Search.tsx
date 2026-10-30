import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { useWindowVirtualizer } from '@tanstack/react-virtual';
import { DEFAULT_QUERY, type MatchMode, type Query, type SortKey } from '@eol/wordlist/query';
import { DECIDED_NAMES, WordFlag, type DecidedName } from '@eol/wordlist/format';
import { useSearch } from './useSearch';
import { paramsToQuery, queryToUrl } from './urlState';
import { plural } from '../charts/format';
import './search.css';

const ROW = 52;
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

/** What decided a word, in a row's few words. */
const ROW_LABEL: Readonly<Record<DecidedName, string>> = {
  none: 'No model or engine',
  model_pipeline: 'Model pipeline',
  model_alone: 'Model alone',
  engine: 'Synthetic engine',
};

interface Props {
  /** what decided each word, short labels, by `DECIDED` name */
  readonly decidedLabels: Readonly<Record<DecidedName, string>>;
  /** each value's count in the whole list, for the filter's labels */
  readonly decidedCounts: Readonly<Record<DecidedName, number>>;
  readonly maxLength: number;
  /** words to start from, each from the vetted example list */
  readonly examples: readonly string[];
}

/** Search and filter the whole list, in the browser. */
export default function Search({ decidedLabels, decidedCounts, maxLength, examples }: Props) {
  const [query, setQuery] = useState<Query>(DEFAULT_QUERY);
  const [ready, setReady] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);

  // The query comes from the URL once, after the first paint, and goes back to
  // it on every change, so a search is a link.
  useEffect(() => {
    setQuery(paramsToQuery(new URLSearchParams(window.location.search)));
    setReady(true);
  }, []);
  useEffect(() => {
    if (!ready) return;
    const url = queryToUrl(window.location.pathname, query);
    if (url !== window.location.pathname + window.location.search) history.replaceState(null, '', url);
  }, [query, ready]);

  const search = useSearch(query);
  const set = (patch: Partial<Query>) => setQuery((q) => ({ ...q, ...patch }));
  const mode = MODES.find((m) => m.mode === query.mode) ?? MODES[0]!;
  const filtered =
    query.decided.length > 0 ||
    query.letters.length > 0 ||
    query.minLength !== DEFAULT_QUERY.minLength ||
    query.maxLength !== DEFAULT_QUERY.maxLength ||
    !query.includeContested;
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

            <Group legend="What decided it" hint="Any, unless you choose">
              {DECIDED_NAMES.map((name) => (
                <label key={name} className="opt">
                  <input
                    type="checkbox"
                    checked={query.decided.includes(name)}
                    onChange={() => set({ decided: toggle(query.decided, name) })}
                  />
                  <span className="opt-label">{decidedLabels[name]}</span>
                  <span className="opt-n">{full(decidedCounts[name])}</span>
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

            <Group legend="Model's verdict">
              <label className="opt">
                <input
                  type="checkbox"
                  checked={!query.includeContested}
                  onChange={(e) => set({ includeContested: !e.target.checked })}
                />
                <span className="opt-label">Leave out words a language model called invalid</span>
              </label>
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
          <Count search={search} text={query.text} />
          {search.status === 'ready' && !query.text && !filtered && (
            <div className="start-from">
              <p>Every word of the list is here, in your browser. Start from one:</p>
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
            <Rows count={search.count} rowAt={search.rowAt} />
          )}
        </section>
      </div>
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

function Rows({ count, rowAt }: { count: number; rowAt: ReturnType<typeof useSearch>['rowAt'] }) {
  const list = useRef<HTMLOListElement>(null);
  const [margin, setMargin] = useState(0);
  useEffect(() => {
    const measure = () => setMargin((list.current?.getBoundingClientRect().top ?? 0) + window.scrollY);
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(document.body);
    return () => ro.disconnect();
  }, []);

  const virtualizer = useWindowVirtualizer({ count, estimateSize: () => ROW, overscan: 10, scrollMargin: margin });
  const items = virtualizer.getVirtualItems();
  const names = useMemo(() => DECIDED_NAMES, []);

  return (
    <ol
      ref={list}
      className="rows"
      aria-label="Matching words"
      style={{ height: `${virtualizer.getTotalSize()}px` }}
    >
      {items.map((item) => {
        const row = rowAt(item.index);
        return (
          <li
            key={item.key}
            className="row"
            style={{ transform: `translateY(${item.start - virtualizer.options.scrollMargin}px)` }}
          >
            {row ? (
              <>
                <span className="row-word word">{row.word}</span>
                <span className="row-meta">
                  <span>{plural(row.word.length, 'letter')}</span>
                  <span className={`decided d-${names[row.decided]}`}>{ROW_LABEL[names[row.decided]!]}</span>
                  {row.added && <span className="row-date">added {shortDate(row.added)}</span>}
                  {(row.flags & WordFlag.LlmSaysInvalid) !== 0 && (
                    <span className="flag" title="One pass of a language model called it invalid; the list kept it.">
                      a model called it invalid
                    </span>
                  )}
                </span>
              </>
            ) : (
              <span className="row-wait" aria-hidden="true" />
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
