import { writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { ROOT } from './paths.ts';
import type { Post } from './posts.ts';

/**
 * RSS and a sitemap, neither of which the old site had.
 *
 * `jekyll-feed` and `jekyll-sitemap` were never in its plugin list, so
 * `/feed.xml` and `/sitemap.xml` both 404 today. Anyone wanting to follow the
 * daily log had to check manually.
 */
const SITE = 'https://english-openlist.pages.dev';
const PUBLIC = resolve(ROOT, 'site/public');

/** XML has five characters that cannot appear raw in text or an attribute. */
function xml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

const STATIC_PAGES = ['/', '/shape', '/use', '/as-it-is', '/blog'];

export async function writeFeeds(posts: readonly Post[]): Promise<string[]> {
  const written: string[] = [];

  // The 40 most recent. A reader wants what is new, and the full 92 would make
  // the feed larger than the page it describes.
  const recent = posts.slice(0, 40);

  const rss = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>English OpenList — daily log</title>
    <link>${SITE}/blog</link>
    <description>What the nightly validation pipeline found, every day.</description>
    <language>en</language>
    <atom:link href="${SITE}/feed.xml" rel="self" type="application/rss+xml"/>
${recent
  .map(
    (post) => `    <item>
      <title>${xml(post.title)}</title>
      <link>${SITE}/blog/${post.date}</link>
      <guid isPermaLink="true">${SITE}/blog/${post.date}</guid>
      <pubDate>${new Date(`${post.date}T00:00:00Z`).toUTCString()}</pubDate>
      <description>${xml(
        post.stats.totalValid
          ? `${post.stats.totalValid.toLocaleString('en-US')} valid words. ` +
              `${post.stats.promotedToday ?? 0} promoted from the invalid list.`
          : post.excerpt,
      )}</description>
    </item>`,
  )
  .join('\n')}
  </channel>
</rss>
`;
  await writeFile(resolve(PUBLIC, 'feed.xml'), rss);
  written.push('feed.xml');

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${STATIC_PAGES.map((path) => `  <url><loc>${SITE}${path}</loc></url>`).join('\n')}
${posts.map((post) => `  <url><loc>${SITE}/blog/${post.date}</loc><lastmod>${post.date}</lastmod></url>`).join('\n')}
</urlset>
`;
  await writeFile(resolve(PUBLIC, 'sitemap.xml'), sitemap);
  written.push('sitemap.xml');

  const robots = `User-agent: *
Allow: /

Sitemap: ${SITE}/sitemap.xml
`;
  await writeFile(resolve(PUBLIC, 'robots.txt'), robots);
  written.push('robots.txt');

  return written;
}
