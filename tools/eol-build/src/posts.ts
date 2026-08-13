import { readdir, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { marked } from 'marked';
import { POSTS_DIR } from './paths.ts';

/**
 * The daily log, read from `_posts/` at build time.
 *
 * Markdown is rendered here rather than in the browser, so `marked` is a build
 * dependency and never reaches a visitor. The pipeline writes a new post every
 * morning and commits it, which pushes `main`, which rebuilds this site — so the
 * blog stays current with no pipeline change at all.
 */
export type Post = {
  readonly date: string;
  readonly title: string;
  readonly excerpt: string;
  readonly html: string;
  /** The whole-list distributions the post embedded, when it carried them. */
  readonly charts: {
    readonly wordLength?: { labels: string[]; values: number[] };
    readonly startingLetter?: { labels: string[]; values: number[] };
  } | null;
  /** Figures lifted out of the prose so the index can show them. */
  readonly stats: {
    readonly totalValid?: number;
    readonly addedToday?: number;
    readonly promotedToday?: number;
  };
  readonly promoted: readonly string[];
};

const FRONT_MATTER = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?/;

/**
 * The generated posts use six fixed fields and no nested YAML, so this reads
 * them directly rather than pulling in a YAML parser for `title:` and `date:`.
 */
function frontMatter(source: string): { fields: Record<string, string>; body: string } {
  const match = FRONT_MATTER.exec(source);
  if (!match) return { fields: {}, body: source };

  const fields: Record<string, string> = {};
  for (const line of match[1]!.split('\n')) {
    const at = line.indexOf(':');
    if (at === -1) continue;
    const key = line.slice(0, at).trim();
    let value = line.slice(at + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    fields[key] = value;
  }
  return { fields, body: source.slice(match[0].length) };
}

const CHART_DATA = /<script id="daily-chart-data" type="application\/json">([\s\S]*?)<\/script>/;

function number(body: string, label: string): number | undefined {
  // The generator writes these as `- **Total valid words now:** **378,891**`.
  const found = new RegExp(`\\*\\*${label}:?\\*\\*[^\\d]*([\\d,]+)`, 'i').exec(body);
  if (!found) return undefined;
  const value = Number(found[1]!.replace(/,/g, ''));
  return Number.isFinite(value) ? value : undefined;
}

export async function loadPosts(): Promise<Post[]> {
  let files: string[];
  try {
    files = (await readdir(POSTS_DIR)).filter((f) => f.endsWith('.md'));
  } catch {
    return [];
  }

  const posts: Post[] = [];

  for (const file of files) {
    const source = await readFile(resolve(POSTS_DIR, file), 'utf8');
    const { fields, body } = frontMatter(source);

    const date = /^(\d{4}-\d{2}-\d{2})/.exec(file)?.[1] ?? (fields['date'] ?? '').slice(0, 10);
    if (!date) continue;

    let charts: Post['charts'] = null;
    const chartMatch = CHART_DATA.exec(body);
    if (chartMatch) {
      try {
        charts = JSON.parse(chartMatch[1]!) as Post['charts'];
      } catch {
        charts = null;
      }
    }

    const promoted = /```text\n([\s\S]*?)```/.exec(body)?.[1]?.trim().split(/\s+/).filter(Boolean) ?? [];

    // Everything the old site loaded from a CDN is removed rather than
    // reproduced: an unpinned Chart.js tag, the Jekyll asset script, the canvas
    // placeholders they drew into, and the JSON blob feeding them. The figures
    // are kept in `charts` and drawn by this site's own components.
    const cleaned = body
      .replace(CHART_DATA, '')
      .replace(/<script[\s\S]*?<\/script>/g, '')
      .replace(/<div class="daily-update-chart-container">[\s\S]*?<\/div>/g, '')
      .replace(/^#{1,2} .*$/m, '')
      .replace(/^### (Starting Letter Distribution|Word Length Distribution)\s*$/gm, '')
      .replace(/^## Interactive Statistics\s*$/gm, '')
      .trim();

    posts.push({
      date,
      title: fields['title'] ?? `Daily update ${date}`,
      excerpt: fields['excerpt'] ?? '',
      html: await marked.parse(cleaned, { async: true }),
      charts,
      // Built by omission rather than by assigning undefined: the early posts
      // genuinely recorded no figures, and `"totalValid": null` in the JSON
      // would claim a measurement of zero where there was none.
      stats: Object.fromEntries(
        Object.entries({
          totalValid: number(cleaned, 'Total valid words now'),
          addedToday: number(cleaned, 'Total words added today'),
          promotedToday: number(cleaned, 'Words promoted from invalid list'),
        }).filter(([, value]) => value !== undefined),
      ),
      promoted,
    });
  }

  // Newest first, which is the order the index wants and the reverse of readdir.
  posts.sort((a, b) => (a.date < b.date ? 1 : -1));
  return posts;
}
