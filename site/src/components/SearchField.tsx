import { useId } from 'react';
import type { MatchMode } from '@eol/wordlist/query';

const MODES: { readonly value: MatchMode; readonly label: string; readonly hint: string }[] = [
  { value: 'prefix', label: 'starts with', hint: 'zy' },
  { value: 'contains', label: 'contains', hint: 'zyme' },
  { value: 'suffix', label: 'ends with', hint: 'ing' },
  { value: 'pattern', label: 'pattern', hint: 'c_t or *zz*' },
  { value: 'regex', label: 'regex', hint: '^q[^u]' },
];

export function SearchField({
  text,
  mode,
  onText,
  onMode,
}: {
  text: string;
  mode: MatchMode;
  onText: (value: string) => void;
  onMode: (value: MatchMode) => void;
}) {
  const inputId = useId();
  const active = MODES.find((m) => m.value === mode) ?? MODES[0]!;

  return (
    <div className="flex flex-col gap-3">
      <label htmlFor={inputId} className="sr-only">
        Search the word list
      </label>
      <input
        id={inputId}
        value={text}
        onChange={(event) => onText(event.target.value)}
        placeholder={active.hint}
        autoComplete="off"
        autoCapitalize="off"
        autoCorrect="off"
        spellCheck={false}
        className="w-full border-b border-rule-strong bg-transparent pb-2 font-display text-4xl
                   tracking-tight text-ink outline-none transition-colors duration-150
                   placeholder:text-ink-faint/50 focus:border-accent sm:text-5xl"
      />

      <div
        role="radiogroup"
        aria-label="How the search text is matched"
        className="flex flex-wrap divide-x divide-rule overflow-hidden rounded-[3px] border border-rule bg-surface"
      >
        {MODES.map((option) => {
          const selected = option.value === mode;
          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => onMode(option.value)}
              className={`h-[34px] px-3 text-sm transition-colors duration-150 ${
                selected
                  ? 'bg-accent-wash text-accent'
                  : 'text-ink-soft hover:bg-sunken hover:text-ink'
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
