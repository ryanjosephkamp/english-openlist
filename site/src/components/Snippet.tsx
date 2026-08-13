import { useCopy } from '../util/useCopy.ts';

/**
 * A code block with a copy button and, where there is one, the output it
 * actually produced.
 *
 * `output` is not decoration. Every snippet on this site was run before it
 * shipped, and printing what came back is the difference between "here is some
 * code" and "here is code that works, and here is how you know."
 */
export function Snippet({
  id,
  title,
  note,
  code,
  output,
}: {
  id: string;
  title?: string;
  note?: string;
  code: string;
  output?: string;
}) {
  const { copied, copy } = useCopy();

  return (
    <figure className="flex flex-col gap-2">
      {(title || note) && (
        <figcaption className="flex flex-col gap-1">
          {title && <h3 className="label">{title}</h3>}
          {note && <p className="text-sm text-ink-soft">{note}</p>}
        </figcaption>
      )}

      <div className="relative rounded-[3px] border border-rule bg-surface">
        <button
          type="button"
          onClick={() => copy(id, code)}
          className="absolute top-2 right-2 rounded-[3px] border border-rule bg-surface px-2 py-1
                     font-mono text-[10px] text-ink-faint transition-colors duration-150
                     hover:border-accent hover:bg-accent-wash hover:text-accent"
        >
          {copied === id ? 'copied' : 'copy'}
        </button>

        <pre className="overflow-x-auto p-4 pr-16 font-mono text-[13px] leading-relaxed text-ink">
          <code>{code}</code>
        </pre>

        {output && (
          <div className="border-t border-rule bg-sunken px-4 py-3">
            <div className="label mb-1">What it printed</div>
            <pre className="overflow-x-auto font-mono text-[12px] leading-relaxed text-ink-soft">
              <code>{output}</code>
            </pre>
          </div>
        )}
      </div>
    </figure>
  );
}
