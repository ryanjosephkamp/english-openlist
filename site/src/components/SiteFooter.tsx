type Link = {
  readonly label: string;
  readonly href: string;
  readonly note: string;
};

const DATASET_LINKS: Link[] = [
  {
    label: 'Hugging Face',
    href: 'https://huggingface.co/datasets/ryanjosephkamp/english-openlist',
    note: 'the dataset',
  },
  {
    label: 'GitHub',
    href: 'https://github.com/ryanjosephkamp/english-openlist',
    note: 'how it is built',
  },
  {
    label: 'Ars Magna',
    href: 'https://ars-magna.pages.dev',
    note: 'anagrams from this list',
  },
];

const AUTHOR_LINKS: Link[] = [
  { label: 'Website', href: 'https://ryanjosephkamp.github.io', note: 'ryanjosephkamp.github.io' },
  { label: 'GitHub', href: 'https://github.com/ryanjosephkamp/', note: 'other projects' },
  { label: 'Sponsor', href: 'https://github.com/sponsors/ryanjosephkamp', note: 'support the work' },
];

/**
 * Footer links get the same treatment as the filter controls — hairline
 * borders, a wash on hover — so they read as part of the same object rather
 * than as a strip of chrome bolted underneath it.
 */
function LinkButton({ link }: { link: Link }) {
  return (
    <a
      href={link.href}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex items-baseline gap-2 rounded-[3px] border border-rule bg-surface px-3
                 py-1.5 text-sm text-ink-soft transition-colors duration-150 hover:border-accent
                 hover:bg-accent-wash hover:text-accent"
    >
      <span className="font-medium">{link.label}</span>
      <span className="font-mono text-[10px] text-ink-faint transition-colors duration-150 group-hover:text-accent">
        {link.note}
      </span>
    </a>
  );
}

function Group({ title, links }: { title: string; links: readonly Link[] }) {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="label">{title}</h2>
      <div className="flex flex-wrap gap-2">
        {links.map((link) => (
          <LinkButton key={link.href} link={link} />
        ))}
      </div>
    </div>
  );
}

export function SiteFooter({ builtAt }: { builtAt: string | null }) {
  return (
    <footer className="mt-20 border-t border-rule-strong pt-8">
      <div className="flex flex-col gap-7 sm:flex-row sm:gap-16">
        <Group title="English OpenList" links={DATASET_LINKS} />
        <Group title="Ryan Kamp" links={AUTHOR_LINKS} />
      </div>

      <div className="mt-8 border-t border-rule pt-5 text-sm text-ink-faint">
        <p>
          Built by{' '}
          <a
            href="https://ryanjosephkamp.github.io"
            target="_blank"
            rel="noopener noreferrer"
            className="text-ink-soft underline decoration-rule-strong underline-offset-4
                       transition-colors duration-150 hover:text-accent hover:decoration-accent"
          >
            Ryan Kamp
          </a>
          . The dataset and this site are MIT licensed. Word validity comes from the sources each
          entry names; this site adds no judgement of its own.
        </p>
        {builtAt && (
          <p className="mt-2 font-mono text-[11px]">
            Rebuilt from the live dataset at {builtAt.slice(0, 16).replace('T', ' ')} UTC
          </p>
        )}
      </div>
    </footer>
  );
}
