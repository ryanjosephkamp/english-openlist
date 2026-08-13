import { useEffect, useState } from 'react';
import { n } from '../util/format.ts';

export type Post = {
  readonly date: string;
  readonly title: string;
  readonly excerpt: string;
  readonly html: string;
  readonly charts: {
    wordLength?: { labels: string[]; values: number[] };
    startingLetter?: { labels: string[]; values: number[] };
  } | null;
  readonly stats: {
    readonly totalValid?: number;
    readonly addedToday?: number;
    readonly promotedToday?: number;
  };
  readonly promoted: readonly string[];
};

let cached: Promise<Post[]> | null = null;

function loadPosts(): Promise<Post[]> {
  if (!cached) {
    const url = `${import.meta.env.BASE_URL}data/posts.json`.replace(/\/{2,}/g, '/');
    cached = fetch(url).then((r) => {
      if (!r.ok) throw new Error(`posts.json: HTTP ${r.status}`);
      return r.json() as Promise<Post[]>;
    });
  }
  return cached;
}

export function usePosts(): { posts: Post[] | null; error: string | null } {
  const [posts, setPosts] = useState<Post[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    loadPosts()
      .then((p) => live && setPosts(p))
      .catch((cause: unknown) => {
        if (live) setError(cause instanceof Error ? cause.message : String(cause));
      });
    return () => {
      live = false;
    };
  }, []);

  return { posts, error };
}

/**
 * A day's figures, drawn as a run of columns.
 *
 * The old posts each embedded ~1.1 KB of JSON describing the whole list's
 * distribution and loaded an unpinned Chart.js from a CDN to draw it — 92 times,
 * for a distribution that barely moves. The data is kept; the CDN is not.
 */
function Sparkline({ values, label }: { values: readonly number[]; label: string }) {
  const max = Math.max(...values, 1);
  const W = 320;
  const H = 44;
  const step = W / values.length;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[20rem]" role="img" aria-label={label}>
      {values.map((v, i) => (
        <rect
          key={i}
          x={i * step}
          y={H - (v / max) * H}
          width={Math.max(1, step - 1)}
          height={(v / max) * H}
          fill="var(--color-accent)"
          fillOpacity="0.85"
        />
      ))}
    </svg>
  );
}

export function BlogIndex({ posts }: { posts: readonly Post[] }) {
  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col gap-3">
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h1 className="font-display text-3xl tracking-tight sm:text-4xl">The daily log</h1>
          <a
            href="/feed.xml"
            className="rounded-[3px] border border-rule bg-surface px-3 py-1.5 text-sm text-ink-soft transition-colors duration-150 hover:border-accent hover:bg-accent-wash hover:text-accent"
          >
            RSS
          </a>
        </div>
        <p className="max-w-[64ch] text-ink-soft">
          Every night at midnight UTC the pipeline validates about a thousand entries from the
          9,275,411-word invalid list and writes up what it found. {posts.length} posts, newest
          first. Most nights nothing is promoted, and the post says so.
        </p>
      </section>

      <ol className="flex flex-col">
        {posts.map((post) => (
          <li key={post.date} className="border-t border-rule last:border-b">
            <a
              href={`/blog/${post.date}`}
              className="group flex flex-wrap items-baseline gap-x-4 gap-y-1 py-3 transition-colors duration-150"
            >
              <span className="font-mono text-[13px] text-ink-soft transition-colors duration-150 group-hover:text-accent">
                {post.date}
              </span>
              <span className="text-sm text-ink-faint">
                {post.stats.totalValid ? `${n(post.stats.totalValid)} valid` : 'no figures recorded'}
              </span>
              {post.promoted.length > 0 && (
                <span className="font-mono text-[12px] text-accent">
                  +{post.promoted.length} promoted: {post.promoted.slice(0, 3).join(', ')}
                </span>
              )}
            </a>
          </li>
        ))}
      </ol>
    </div>
  );
}

export function BlogPost({ post, previous, next }: { post: Post; previous?: Post; next?: Post }) {
  return (
    <article className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <div className="label">{post.date}</div>
        <h1 className="font-display text-3xl tracking-tight sm:text-4xl">
          What the pipeline found
        </h1>
        {post.stats.totalValid && (
          <p className="text-ink-soft">
            {n(post.stats.totalValid)} valid words after this run
            {post.promoted.length > 0 && (
              <>
                {' '}
                · promoted{' '}
                {post.promoted.map((word, i) => (
                  <span key={word}>
                    {i > 0 && ', '}
                    <a
                      href={`/word/${encodeURIComponent(word)}`}
                      className="font-mono text-[13px] underline decoration-rule-strong underline-offset-4 transition-colors duration-150 hover:text-accent hover:decoration-accent"
                    >
                      {word}
                    </a>
                  </span>
                ))}
              </>
            )}
          </p>
        )}
      </header>

      {post.charts?.wordLength && post.charts.startingLetter && (
        <div className="flex flex-wrap gap-8 rounded-[3px] border border-rule bg-surface p-4">
          <div className="flex flex-col gap-1">
            <span className="label">Word length</span>
            <Sparkline values={post.charts.wordLength.values} label="Word length distribution" />
          </div>
          <div className="flex flex-col gap-1">
            <span className="label">Starting letter</span>
            <Sparkline
              values={post.charts.startingLetter.values}
              label="Starting letter distribution"
            />
          </div>
          <p className="w-full text-sm text-ink-faint">
            These describe the whole list, not the day — they barely move.{' '}
            <a href="/shape">The shape page</a> draws them properly.
          </p>
        </div>
      )}

      <div
        className="post flex flex-col gap-3 text-ink-soft"
        // The source is this repo's own `_posts/`, rendered to HTML at build
        // time by the same build that ships it. Nothing user-supplied reaches
        // here, and every script tag the generator emitted is stripped first.
        dangerouslySetInnerHTML={{ __html: post.html }}
      />

      <nav className="flex flex-wrap justify-between gap-3 border-t border-rule pt-5 text-sm">
        {previous ? (
          <a href={`/blog/${previous.date}`} className="text-ink-soft hover:text-accent">
            ← {previous.date}
          </a>
        ) : (
          <span />
        )}
        <a href="/blog" className="text-ink-soft hover:text-accent">
          All posts
        </a>
        {next ? (
          <a href={`/blog/${next.date}`} className="text-ink-soft hover:text-accent">
            {next.date} →
          </a>
        ) : (
          <span />
        )}
      </nav>
    </article>
  );
}
