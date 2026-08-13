import { useCallback, useEffect, useMemo } from 'react';
import { DEFAULT_QUERY, type Query } from '@eol/wordlist/query';
import { useRoute, useLinkInterception } from './util/router.ts';
import { paramsToQuery, queryToUrl } from './util/urlState.ts';
import { useSearch } from './state/useSearch.ts';
import { SiteHeader } from './components/SiteHeader.tsx';
import { SiteFooter } from './components/SiteFooter.tsx';
import { SearchField } from './components/SearchField.tsx';
import { Filters } from './components/Filters.tsx';
import { ResultList } from './components/ResultList.tsx';
import { WordPage } from './pages/WordPage.tsx';
import { UsePage } from './pages/UsePage.tsx';
import { ShapePage } from './pages/ShapePage.tsx';
import { AsItIsPage } from './pages/AsItIsPage.tsx';
import { PlaceholderPage } from './pages/PlaceholderPage.tsx';
import { BlogIndex, BlogPost, usePosts } from './pages/BlogPage.tsx';
import { n, millis, bytes } from './util/format.ts';

export function App() {
  const { route, navigate } = useRoute();
  useLinkInterception(navigate);

  const query = useMemo<Query>(
    () => paramsToQuery(new URLSearchParams(route.search)),
    [route.search],
  );

  const search = useSearch(query);

  const update = useCallback(
    (patch: Partial<Query>) => {
      navigate(queryToUrl('/', { ...query, ...patch }), { replace: true });
    },
    [navigate, query],
  );

  const word = route.path.startsWith('/word/')
    ? decodeURIComponent(route.path.slice('/word/'.length))
    : null;

  // The title is the tab, the history entry, and what a shared link is called.
  // A single-page app has to set it per route or every page is named after the
  // first one — which is what /shape and /use were called until now.
  useEffect(() => {
    document.title = titleFor(route.path, word);
  }, [route.path, word]);

  return (
    <>
      <SiteHeader path={route.path} />

      <main className="mx-auto max-w-5xl px-6 pt-10 pb-24">
        {search.status === 'failed' ? (
          <Notice
            title="The word list could not be loaded"
            body={search.failure ?? 'The request failed.'}
          />
        ) : word !== null ? (
          <WordPage word={word} search={search} />
        ) : route.path === '/use' ? (
          <UsePage />
        ) : route.path === '/shape' ? (
          <ShapePage />
        ) : route.path === '/as-it-is' ? (
          <AsItIsPage manifest={search.manifest} />
        ) : route.path.startsWith('/blog') ? (
          <Blog path={route.path} />
        ) : route.path === '/' ? (
          <Explorer query={query} search={search} update={update} />
        ) : (
          <PlaceholderPage
            title="There is nothing at this address"
            body={`Nothing on this site answers to ${route.path}. If you were looking for a particular word, the search will find it.`}
          />
        )}

        <SiteFooter builtAt={search.manifest?.builtAt ?? null} />
      </main>
    </>
  );
}

function Explorer({
  query,
  search,
  update,
}: {
  query: Query;
  search: ReturnType<typeof useSearch>;
  update: (patch: Partial<Query>) => void;
}) {
  const loading = search.status === 'loading';
  const filtered = search.count !== search.manifest?.wordCount;

  return (
    <div className="flex flex-col gap-10">
      <section className="flex flex-col gap-4">
        <h1 className="font-display text-3xl tracking-tight sm:text-4xl">
          {search.manifest ? n(search.manifest.wordCount) : '378,891'} English words, and where
          each one came from
        </h1>
        <p className="max-w-[62ch] text-ink-soft">
          The whole list is in your browser — {search.transferred ? bytes(search.transferred) : '666 KB'}{' '}
          over the wire, then every search runs locally. Nothing is sent anywhere.
        </p>
      </section>

      <SearchField
        text={query.text}
        mode={query.mode}
        onText={(text) => update({ text })}
        onMode={(mode) => update({ mode })}
      />

      {/* The count before the results, because on most queries it is the more
          useful fact and it arrives first. */}
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1" aria-live="polite">
        {loading ? (
          <span className="font-display text-3xl text-ink-faint">Loading the list…</span>
        ) : search.error ? (
          <span className="font-display text-2xl text-accent">{search.error}</span>
        ) : (
          <>
            <span className="font-display text-3xl text-accent tabular-nums">
              {n(search.count)}
            </span>
            <span className="text-sm text-ink-faint">
              {search.count === 1 ? 'word' : 'words'}
              {filtered && search.manifest
                ? ` of ${n(search.manifest.wordCount)}`
                : ''}{' '}
              · scanned in {millis(search.millis)}
            </span>
          </>
        )}
      </div>

      {search.manifest && (
        <Filters query={query} counts={search.manifest.intakeCounts} onChange={update} />
      )}

      {!loading && search.count === 0 && !search.error ? (
        <NoResults query={query} onReset={() => update(DEFAULT_QUERY)} />
      ) : (
        <ResultList count={search.count} rowAt={search.rowAt} />
      )}

      {search.manifest && (
        <p className="text-sm text-ink-faint">
          Dates are mostly bulk-load dates: 372,187 of these words carry one of three, the days the
          founding intakes landed. Only 24 have been added one at a time since.{' '}
          <a
            href="/as-it-is"
            className="underline decoration-rule-strong underline-offset-4 transition-colors duration-150 hover:text-accent"
          >
            What else to know about this list
          </a>
          .
        </p>
      )}
    </div>
  );
}

function Blog({ path }: { path: string }) {
  const { posts, error } = usePosts();

  if (error) {
    return (
      <Notice title="The daily log could not be loaded" body={error} />
    );
  }
  if (!posts) return <p className="py-16 text-center text-ink-faint">Reading the log…</p>;

  const date = path === '/blog' ? null : path.slice('/blog/'.length).replace(/\/$/, '');
  if (!date) return <BlogIndex posts={posts} />;

  const at = posts.findIndex((p) => p.date === date);
  if (at === -1) {
    return (
      <PlaceholderPage
        title={`No post for ${date}`}
        body={`The pipeline has written ${posts.length} of these, from ${posts[posts.length - 1]?.date} to ${posts[0]?.date}, but not one for that day. Two days in June are genuinely missing rather than hidden.`}
      />
    );
  }

  // Newest first, so the earlier post is the *next* index.
  return (
    <BlogPost
      post={posts[at]!}
      {...(posts[at + 1] ? { previous: posts[at + 1]! } : {})}
      {...(posts[at - 1] ? { next: posts[at - 1]! } : {})}
    />
  );
}

const SITE = 'English OpenList';

function titleFor(path: string, word: string | null): string {
  if (word) return `${word} — ${SITE}`;
  switch (path) {
    case '/':
      return `${SITE} — 378,891 English words, and where each one came from`;
    case '/shape':
      return `The shape of the list — ${SITE}`;
    case '/use':
      return `Use it in your own thing — ${SITE}`;
    case '/as-it-is':
      return `The list as it is — ${SITE}`;
    case '/blog':
      return `Daily log — ${SITE}`;
    default:
      if (path.startsWith('/blog/')) return `${path.slice('/blog/'.length)} — daily log — ${SITE}`;
      return `Not found — ${SITE}`;
  }
}

function Notice({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-[3px] border border-accent bg-accent-wash p-5">
      <h2 className="font-display text-xl text-accent">{title}</h2>
      <p className="mt-1 text-sm text-ink-soft">{body}</p>
    </div>
  );
}

function NoResults({ query, onReset }: { query: Query; onReset: () => void }) {
  return (
    <div className="rounded-[3px] border border-rule bg-surface p-8 text-center">
      <p className="font-display text-xl text-ink">
        {query.text ? `Nothing matches “${query.text}”` : 'Nothing matches these filters'}
      </p>
      <button
        type="button"
        onClick={onReset}
        className="mt-3 text-sm text-ink-soft underline decoration-rule-strong underline-offset-4 transition-colors duration-150 hover:text-accent hover:decoration-accent"
      >
        Clear everything
      </button>
    </div>
  );
}
