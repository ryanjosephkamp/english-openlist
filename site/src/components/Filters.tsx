import { useId } from 'react';
import type { Charset, Query, SortKey } from '@eol/wordlist/query';
import { INTAKE_NAMES, type IntakeName } from '@eol/wordlist/format';
import { INTAKE_LABEL, n } from '../util/format.ts';

const LETTERS = 'abcdefghijklmnopqrstuvwxyz'.split('');

const CHARSETS: { value: Charset; label: string; count?: string }[] = [
  { value: 'any', label: 'Any' },
  { value: 'alpha', label: 'Strictly a–z' },
  { value: 'hyphen', label: 'Has a hyphen', count: '188' },
  { value: 'accent', label: 'Has an accent', count: '2' },
];

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="label">{label}</span>
      {children}
    </div>
  );
}

const CONTROL =
  'h-[34px] rounded-[3px] border border-rule bg-surface px-2 text-sm text-ink transition-colors duration-150 hover:border-rule-strong';

export function Filters({
  query,
  counts,
  onChange,
}: {
  query: Query;
  counts: Readonly<Record<string, number>>;
  onChange: (patch: Partial<Query>) => void;
}) {
  const minId = useId();
  const maxId = useId();
  const sortId = useId();

  const toggleIntake = (name: IntakeName) => {
    const next = query.intakes.includes(name)
      ? query.intakes.filter((i) => i !== name)
      : [...query.intakes, name];
    onChange({ intakes: next });
  };

  const toggleLetter = (letter: string) => {
    const next = query.letters.includes(letter)
      ? query.letters.filter((l) => l !== letter)
      : [...query.letters, letter];
    onChange({ letters: next });
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap gap-x-8 gap-y-5">
        <Field label="Length">
          <div className="flex items-center gap-2">
            <label htmlFor={minId} className="sr-only">
              Minimum length
            </label>
            <input
              id={minId}
              type="number"
              min={1}
              max={47}
              value={query.minLength}
              onChange={(e) => onChange({ minLength: clamp(e.target.value, 1) })}
              className={`${CONTROL} w-16`}
            />
            <span className="text-sm text-ink-faint">to</span>
            <label htmlFor={maxId} className="sr-only">
              Maximum length
            </label>
            <input
              id={maxId}
              type="number"
              min={1}
              max={47}
              value={query.maxLength}
              onChange={(e) => onChange({ maxLength: clamp(e.target.value, 47) })}
              className={`${CONTROL} w-16`}
            />
          </div>
        </Field>

        <Field label="Sort">
          <div className="flex items-center gap-2">
            <label htmlFor={sortId} className="sr-only">
              Sort by
            </label>
            <select
              id={sortId}
              value={query.sort}
              onChange={(e) => onChange({ sort: e.target.value as SortKey })}
              className={CONTROL}
            >
              <option value="alpha">Alphabetical</option>
              <option value="length">Length</option>
              <option value="added">Date added</option>
            </select>
            <button
              type="button"
              onClick={() => onChange({ descending: !query.descending })}
              aria-pressed={query.descending}
              className={`${CONTROL} px-3`}
            >
              {query.descending ? 'Descending' : 'Ascending'}
            </button>
          </div>
        </Field>
      </div>

      <Field label="Intake">
        <div className="flex flex-wrap gap-2">
          {INTAKE_NAMES.map((name) => {
            const on = query.intakes.includes(name);
            return (
              <button
                key={name}
                type="button"
                aria-pressed={on}
                onClick={() => toggleIntake(name)}
                className={`flex items-baseline gap-2 rounded-[3px] border px-3 py-1.5 text-sm transition-colors duration-150 ${
                  on
                    ? 'border-accent bg-accent-wash text-accent'
                    : 'border-rule bg-surface text-ink-soft hover:border-rule-strong hover:text-ink'
                }`}
              >
                <span>{INTAKE_LABEL[name]}</span>
                <span className="font-mono text-[10px] text-ink-faint">{n(counts[name] ?? 0)}</span>
              </button>
            );
          })}
          {query.intakes.length > 0 && (
            <button
              type="button"
              onClick={() => onChange({ intakes: [] })}
              className="px-2 text-sm text-ink-faint underline decoration-rule-strong underline-offset-4 transition-colors duration-150 hover:text-accent"
            >
              clear
            </button>
          )}
        </div>
      </Field>

      <Field label="First letter">
        <div className="flex flex-wrap gap-1">
          {LETTERS.map((letter) => {
            const on = query.letters.includes(letter);
            return (
              <button
                key={letter}
                type="button"
                aria-pressed={on}
                aria-label={`Words starting with ${letter}`}
                onClick={() => toggleLetter(letter)}
                className={`h-7 w-7 rounded-[3px] border font-mono text-xs transition-colors duration-150 ${
                  on
                    ? 'border-accent bg-accent-wash text-accent'
                    : 'border-rule bg-surface text-ink-soft hover:border-rule-strong hover:text-ink'
                }`}
              >
                {letter}
              </button>
            );
          })}
          {query.letters.length > 0 && (
            <button
              type="button"
              onClick={() => onChange({ letters: [] })}
              className="px-2 text-sm text-ink-faint underline decoration-rule-strong underline-offset-4 transition-colors duration-150 hover:text-accent"
            >
              clear
            </button>
          )}
        </div>
      </Field>

      {/* Not part of "first letter": every word in the list begins with a-z.
          The 188 hyphenated entries and the two accented ones carry those
          characters internally, so this filters the whole word. */}
      <Field label="Characters">
        <div
          role="radiogroup"
          aria-label="Which characters a word may contain"
          className="flex w-fit flex-wrap divide-x divide-rule overflow-hidden rounded-[3px] border border-rule bg-surface"
        >
          {CHARSETS.map((option) => {
            const on = query.charset === option.value;
            return (
              <button
                key={option.value}
                type="button"
                role="radio"
                aria-checked={on}
                onClick={() => onChange({ charset: option.value })}
                className={`h-[34px] px-3 text-sm transition-colors duration-150 ${
                  on ? 'bg-accent-wash text-accent' : 'text-ink-soft hover:bg-sunken hover:text-ink'
                }`}
              >
                {option.label}
                {option.count !== undefined && (
                  <span className="ml-2 font-mono text-[10px] text-ink-faint">{option.count}</span>
                )}
              </button>
            );
          })}
        </div>
      </Field>

      <label className="flex w-fit items-center gap-2 text-sm text-ink-soft">
        <input
          type="checkbox"
          checked={!query.includeContested}
          onChange={(e) => onChange({ includeContested: !e.target.checked })}
          className="accent-accent"
        />
        Hide the 20,052 entries whose own record says <code className="font-mono text-xs">invalid</code>
      </label>
    </div>
  );
}

function clamp(raw: string, fallback: number): number {
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1 || value > 47) return fallback;
  return value;
}
