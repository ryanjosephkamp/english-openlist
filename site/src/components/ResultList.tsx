import { useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { WordFlag } from '@eol/wordlist/format';
import type { Row } from '../worker/protocol.ts';
import { intakeLabel, intakeName } from '../util/format.ts';

const ROW_HEIGHT = 44;

const INTAKE_DOT: Record<string, string> = {
  twl: 'bg-intake-twl',
  pipeline: 'bg-intake-pipeline',
  synthetic: 'bg-intake-synthetic',
  other: 'bg-intake-other',
};

function Marks({ flags }: { flags: number }) {
  const marks: string[] = [];
  if ((flags & WordFlag.StatusInvalid) !== 0) marks.push('record says invalid');
  if ((flags & WordFlag.AlsoInvalid) !== 0) marks.push('also in the invalid list');
  if (marks.length === 0) return null;

  return (
    <span
      title={marks.join('; ')}
      className="font-mono text-[10px] text-accent"
      aria-label={marks.join('; ')}
    >
      ⚑
    </span>
  );
}

export function ResultList({
  count,
  rowAt,
}: {
  count: number;
  rowAt: (index: number) => Row | undefined;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 12,
  });

  return (
    <div
      ref={scrollRef}
      className="settle max-h-[62vh] overflow-y-auto rounded-[3px] border border-rule bg-surface"
      // The list is the page's main content and is scrolled independently, so it
      // needs to be reachable and scrollable from the keyboard on its own.
      tabIndex={0}
      role="region"
      aria-label="Matching words"
    >
      <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
        {virtualizer.getVirtualItems().map((item) => {
          const row = rowAt(item.index);

          return (
            <div
              key={item.key}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${item.size}px`,
                transform: `translateY(${item.start}px)`,
              }}
              className="flex items-center gap-3 border-b border-rule px-4 last:border-b-0"
            >
              {row ? (
                <>
                  <a
                    href={`/word/${encodeURIComponent(row.word)}`}
                    className="font-display text-lg text-ink transition-colors duration-150 hover:text-accent"
                  >
                    {row.word}
                  </a>
                  <Marks flags={row.flags} />
                  <span className="ml-auto flex items-center gap-3 font-mono text-[11px] text-ink-faint">
                    <span className="tabular-nums">{row.word.length}</span>
                    <span className="hidden items-center gap-1.5 sm:flex">
                      <span
                        aria-hidden
                        className={`inline-block h-1.5 w-1.5 rounded-full ${INTAKE_DOT[intakeName(row.intake)]}`}
                      />
                      {intakeLabel(row.intake)}
                    </span>
                    <span className="hidden w-[5.5rem] text-right md:inline">
                      {row.added || 'no date'}
                    </span>
                  </span>
                </>
              ) : (
                // A page in flight. The row keeps its height so the scrollbar
                // never jumps as content lands.
                <span className="h-3 w-24 animate-pulse rounded-[2px] bg-sunken" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
