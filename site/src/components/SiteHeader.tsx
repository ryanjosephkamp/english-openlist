const NAV = [
  { href: '/', label: 'Explore' },
  { href: '/shape', label: 'Shape' },
  { href: '/use', label: 'Use it' },
  { href: '/as-it-is', label: 'As it is' },
  { href: '/blog', label: 'Daily log' },
] as const;

export function SiteHeader({ path }: { path: string }) {
  return (
    <header className="border-b border-rule">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-6 py-4 sm:flex-row sm:items-baseline sm:justify-between">
        <a
          href="/"
          className="font-display text-lg tracking-tight text-ink transition-colors duration-150 hover:text-accent"
        >
          English OpenList
        </a>

        <nav aria-label="Sections">
          <ul className="-mx-2 flex flex-wrap items-baseline">
            {NAV.map((item) => {
              const active = item.href === '/' ? path === '/' : path.startsWith(item.href);
              return (
                <li key={item.href}>
                  <a
                    href={item.href}
                    aria-current={active ? 'page' : undefined}
                    className={`block px-2 py-1 text-sm transition-colors duration-150 hover:text-accent ${
                      active ? 'text-accent' : 'text-ink-soft'
                    }`}
                  >
                    {item.label}
                  </a>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>
    </header>
  );
}
