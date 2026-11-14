import { useEffect, useRef, useState } from 'react';
import { WordFlag } from '@eol/wordlist/format';
import type { Row } from '../worker/protocol';
import { full, plural } from '../charts/format';
import { lookups } from '../util/lookups';
import { ENGINE_WHAT, joinNames, listedLabels, listedState, listedTone, LISTED_WHAT } from '../util/listed';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const longDate = (iso: string) => `${MONTHS[Number(iso.slice(5, 7)) - 1]} ${Number(iso.slice(8))}, ${iso.slice(0, 4)}`;

interface Props {
  readonly word: string;
  /** the word's row; null when it is not on the list, undefined while it is looked up */
  readonly row: Row | null | undefined;
  /** every day a nightly run has a page in the daily log */
  readonly runDates: ReadonlySet<string>;
  /** days that date more words than a night's run adds, with their counts */
  readonly bulkDates: ReadonlyMap<string, number>;
  readonly onClose: () => void;
  readonly onSearch: (word: string) => void;
}

/**
 * 1 word, everything the list records of it, and where to read more. A modal
 * dialog: on a phone it rises from the bottom like a sheet.
 */
export default function WordPanel({ word, row, runDates, bulkDates, onClose, onSearch }: Props) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [copied, setCopied] = useState<'word' | 'link' | 'failed' | null>(null);

  useEffect(() => {
    const d = dialog.current;
    if (d && !d.open) d.showModal();
  }, []);
  useEffect(() => {
    if (!copied) return;
    const t = setTimeout(() => setCopied(null), 2000);
    return () => clearTimeout(t);
  }, [copied]);

  const copy = (what: 'word' | 'link') => {
    const url = new URL('/', window.location.origin);
    url.searchParams.set('w', word);
    navigator.clipboard
      ?.writeText(what === 'word' ? word : url.toString())
      .then(() => setCopied(what))
      .catch(() => setCopied('failed'));
  };

  const added = row?.added ?? '';
  const bulk = bulkDates.get(added);

  return (
    <dialog
      ref={dialog}
      className="panel"
      aria-labelledby="panel-word"
      onClose={onClose}
      onClick={(e) => {
        // a press on the backdrop lands on the dialog itself
        if (e.target === dialog.current) dialog.current.close();
      }}
    >
      <div className="panel-body">
        <header className="panel-head">
          <p className="panel-kicker">{row === undefined ? 'Looking it up' : row ? 'On the list' : 'Not on the list'}</p>
          <h2 id="panel-word" className="word">
            {word}
          </h2>
          <button type="button" className="panel-close" onClick={() => dialog.current?.close()} aria-label="Close">
            ×
          </button>
        </header>

        {row === null && (
          <p className="panel-note">
            The list holds lowercase a to z only, so a capital, a space, or a hyphen never matches. A word off the list is not
            invalid for good: the nightly run may check it again.
          </p>
        )}

        {row && (
          <dl className="panel-facts">
            <div>
              <dt>Length</dt>
              <dd>{plural(row.word.length, 'letter')}</dd>
            </div>
            <div>
              <dt>Added</dt>
              <dd>
                {!added ? (
                  'No date recorded'
                ) : runDates.has(added) ? (
                  <>
                    {longDate(added)}, by the nightly run. <a href={`/blog/${added}/`}>Read that day's log</a>
                  </>
                ) : bulk !== undefined ? (
                  <>
                    {longDate(added)}, in a single load of {full(bulk)} words
                  </>
                ) : (
                  longDate(added)
                )}
              </dd>
            </div>
            <div>
              <dt>Listed by</dt>
              <dd>
                <ListedBy attested={row.attested} />
              </dd>
            </div>
            <div>
              <dt>Synthetic engine</dt>
              <dd>
                {(row.flags & WordFlag.Engine) !== 0 ? (
                  <>
                    <span className="flag">Made by it</span>
                    <span className="panel-what">{ENGINE_WHAT}</span>
                  </>
                ) : (
                  'Not made by it'
                )}
              </dd>
            </div>
            {(row.flags & WordFlag.AlsoInvalid) !== 0 && (
              <div>
                <dt>Also listed as invalid</dt>
                <dd>The invalid list holds it too; the 2 lists disagree about it.</dd>
              </div>
            )}
          </dl>
        )}

        <section className="panel-look" aria-labelledby="panel-look">
          <h3 id="panel-look">Look it up</h3>
          <ul>
            {lookups(word).map((l) => (
              <li key={l.label}>
                <a href={l.href} target="_blank" rel="noopener">
                  {l.label}
                </a>
              </li>
            ))}
          </ul>
          <p className="panel-note">The list carries no definitions of its own. These open in a new tab.</p>
        </section>

        <div className="panel-actions">
          <button type="button" onClick={() => copy('word')}>
            {copied === 'word' ? 'Copied' : 'Copy the word'}
          </button>
          <button type="button" onClick={() => copy('link')}>
            {copied === 'link' ? 'Copied' : 'Copy a link'}
          </button>
          {row && (
            <button type="button" onClick={() => onSearch(word)}>
              Words that start with it
            </button>
          )}
          {copied === 'failed' && <span className="panel-note">This browser would not copy.</span>}
        </div>
      </div>
    </dialog>
  );
}

/** Which open sources list the word, with what that means. */
function ListedBy({ attested }: { attested: number }) {
  const state = listedState(attested);
  const names = listedLabels(attested);
  return (
    <>
      <span className={`listed ${listedTone(attested)}`}>
        {state === 'listed' ? joinNames(names) : state === 'none' ? 'No open source lists it' : 'Not checked yet'}
      </span>
      <span className="panel-what">
        {state === 'listed' && `${names.length} of the 6 open sources. `}
        {LISTED_WHAT[state]} <a href="/rule/#listed">About the open sources</a>
      </span>
    </>
  );
}
