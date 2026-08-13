/**
 * For a route the navigation offers but the site does not serve yet, and for
 * one it never will.
 *
 * The alternative — falling through to the explorer — is what `/as-it-is` and
 * `/blog` did before this: the word list appeared with the wrong tab marked
 * current, which reads as a broken site rather than an unfinished one.
 */
export function PlaceholderPage({
  title,
  body,
  soon,
}: {
  title: string;
  body: string;
  soon?: boolean;
}) {
  return (
    <div className="flex max-w-[62ch] flex-col gap-4 py-10">
      <h1 className="font-display text-3xl tracking-tight sm:text-4xl">{title}</h1>
      <p className="text-ink-soft">{body}</p>
      <div className="flex flex-wrap gap-2 pt-2">
        <a
          href="/"
          className="rounded-[3px] border border-rule bg-surface px-3 py-1.5 text-sm text-ink-soft transition-colors duration-150 hover:border-accent hover:bg-accent-wash hover:text-accent"
        >
          Search the list
        </a>
        {soon && (
          <a
            href="https://ryanjosephkamp.github.io/english-openlist/"
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-[3px] border border-rule bg-surface px-3 py-1.5 text-sm text-ink-soft transition-colors duration-150 hover:border-accent hover:bg-accent-wash hover:text-accent"
          >
            The daily log, where it lives today →
          </a>
        )}
      </div>
    </div>
  );
}
