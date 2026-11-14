import type { APIRoute } from 'astro';
import { fmt, runHref } from '../util/data';
import { usDate } from '../util/dates';
import { newestFirst, summary } from '../util/runs';

/** The daily log as an RSS feed: the newest 60 runs. */
const ITEMS = 60;

const escape = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

export const GET: APIRoute = ({ site }) => {
  const base = (site ?? new URL('https://english-openlist.pages.dev')).origin;
  const items = newestFirst.slice(0, ITEMS).map((run) => {
    const link = `${base}${runHref(run.date)}`;
    const words = run.words.map((w) => w.word).join(', ');
    const description = [
      `${summary(run)}.`,
      words && `The words: ${words}.`,
      run.total !== null && `The list then held ${fmt(run.total)} words.`,
    ]
      .filter(Boolean)
      .join(' ');
    const at = run.at ?? `${run.date}T00:00:00Z`;
    return `    <item>
      <title>${escape(`${usDate(run.date)}: ${summary(run)}`)}</title>
      <link>${link}</link>
      <guid isPermaLink="true">${link}</guid>
      <pubDate>${new Date(at).toUTCString()}</pubDate>
      <description>${escape(description)}</description>
    </item>`;
  });
  const body = `<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>The English OpenList: daily log</title>
    <link>${base}/blog/</link>
    <description>Every nightly run of the English OpenList: the words it added and how the list changed.</description>
    <language>en-us</language>
${items.join('\n')}
  </channel>
</rss>
`;
  return new Response(body, { headers: { 'Content-Type': 'application/rss+xml; charset=utf-8' } });
};
