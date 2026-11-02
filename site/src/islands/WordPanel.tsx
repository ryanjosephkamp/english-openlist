import { useEffect, useRef, useState } from 'react';
import { DECIDED_NAMES, WordFlag, type DecidedName } from '@eol/wordlist/format';
import type { Row } from '../worker/protocol';
import { plural } from '../charts/format';
import { lookups } from '../util/lookups';

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const longDate = (iso: string) => `${MONTHS[Number(iso.slice(5, 7)) - 1]} ${Number(iso.slice(8))}, ${iso.slice(0, 4)}`;

interface Props {
  readonly word: string;
  /** the word's row; null when it is not on the list, undefined while it is looked up */
  readonly row: Row | null | undefined;
  readonly decidedLabels: Readonly<Record<DecidedName, string>>;
  readonly decidedWhat: Readonly<Record<DecidedName, string>>;
  /** every day a nightly run has a page in the daily log */
  readonly runDates: ReadonlySet<string>;
  /** the days of the large loads that built the list */
  readonly bulkDates: ReadonlySet<string>;
  readonly onClose: () => void;
  readonly onSearch: (word: string) => void;
}

/**
 * 1 word, everything the list records of it, and where to read more. A modal
 * dialog: on a phone it rises from the bottom like a sheet.
 */
export default function WordPanel({ word, row, decidedLabels, decidedWhat, runDates, bulkDates, onClose, onSearch }: Props) {
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

  const name = row ? DECIDED_NAMES[row.decided]! : null;
  const added = row?.added ?? '';

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

        {row && name && (
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
                ) : bulkDates.has(added) ? (
                  <>{longDate(added)}, in 1 of the 3 large loads that built the list</>
                ) : (
                  longDate(added)
                )}
              </dd>
            </div>
            <div>
              <dt>What decided it</dt>
              <dd>
                <span className={`decided d-${name}`}>{decidedLabels[name]}</span>
                <span className="panel-what">{decidedWhat[name]}</span>
              </dd>
            </div>
            {(row.flags & WordFlag.LlmSaysInvalid) !== 0 && (
              <div>
                <dt>A model's note</dt>
                <dd>1 pass of a language model called it invalid, and the list kept it. The note is an opinion, not a verdict.</dd>
              </div>
            )}
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
