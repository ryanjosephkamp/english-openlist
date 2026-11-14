// Checks the built site before it can be deployed. It fails when:
//   - CEOL_PUBLIC is false and a page or script names the CEOL Universe's
//     address, or the page about it exists;
//   - a public file carries a label outside the published vocabularies: the
//     text `withheld_`, a `source` value other than the published intakes, or
//     an `attested_by` key other than the open sources;
//   - a word the start page offers is no longer on the list.
// A word the daily log prints can contain a name these checks look for, so
// such a word is set aside as a whole token first; the name alone still fails.
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { decodeWords, wordAt } from '@eol/wordlist/decode';
import { ATTESTERS } from '@eol/wordlist/format';

const site = fileURLToPath(new URL('..', import.meta.url));
const dist = join(site, 'dist');
const failures = [];

const state = readFileSync(join(site, 'src/util/release-state.ts'), 'utf8');
const ceolPublic = /export const CEOL_PUBLIC = true;/.test(state);
if (!ceolPublic && !/export const CEOL_PUBLIC = false;/.test(state)) failures.push('CEOL_PUBLIC is neither true nor false');

function* files(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) yield* files(path);
    else yield path;
  }
}

const TEXT = /\.(html|js|css|json|txt|xml|svg)$/;
// The CEOL Universe's addresses and its name: nothing public names it before its release.
const CEOL_ADDRESSES = ['common-english-openlist', 'ceol-universe', 'ceol'];
// The only `source` values a public file may carry: the published intakes.
const SOURCES = new Set(['synthetic_generation', 'authoritative_extracts', 'extended_domain_sources', 'free-dictionary', 'invalid_list_recovery']);
const ATTESTER_KEYS = new Set(ATTESTERS);
// `source: "x"`, `"source":"x"`, or `source="x"`, in data, markup, or a script.
const SOURCE_VALUE = /\bsource["']?\s*[:=]\s*["']([^"']*)["']/g;
// `attested_by: [...]` or `"attested_by":[...]`, with its quoted keys.
const ATTESTED_LIST = /\battested_by["']?\s*[:=]\s*\[([^\]]*)\]/g;
const QUOTED = /["']([^"']*)["']/g;

/** The labels in `text` outside the published vocabularies. */
function strayLabels(text) {
  const found = [];
  if (text.includes('withheld_')) found.push('the text withheld_');
  for (const [, value] of text.matchAll(SOURCE_VALUE)) if (!SOURCES.has(value)) found.push(`the source value "${value}"`);
  for (const [, list] of text.matchAll(ATTESTED_LIST)) {
    for (const [, key] of list.matchAll(QUOTED)) if (!ATTESTER_KEYS.has(key)) found.push(`the attested_by key "${key}"`);
  }
  return found;
}

const runs = JSON.parse(readFileSync(join(dist, 'data/runs.json'), 'utf8'));
const runWords = new Set(runs.flatMap((r) => [...r.words.map((w) => w.word), ...r.missing]));
// A run word equal to a name is not set aside: that page needs a person's look.
const masked = [...runWords].filter((w) => CEOL_ADDRESSES.some((n) => w.includes(n) && w !== n));
const mask = masked.length ? new RegExp(`(?<![a-z])(?:${masked.join('|')})(?![a-z])`, 'g') : null;

let read = 0;
for (const path of files(dist)) {
  if (!TEXT.test(path)) continue;
  const rel = relative(dist, path);
  const raw = readFileSync(path, 'utf8');
  read++;
  for (const label of strayLabels(raw)) failures.push(`${rel}: carries ${label}`);
  // the word lists are words, not names: a name can be part of a word
  if (rel.startsWith('downloads/') && rel.endsWith('.txt')) continue;
  let text = raw.toLowerCase();
  if (mask) text = text.replace(mask, '');
  if (!ceolPublic) for (const a of CEOL_ADDRESSES) if (text.includes(a)) failures.push(`${rel}: names ${a} while CEOL_PUBLIC is false`);
}
if (!ceolPublic && existsSync(join(dist, 'universe'))) failures.push('universe/ was built while CEOL_PUBLIC is false');

const manifest = JSON.parse(readFileSync(join(dist, 'data/manifest.json'), 'utf8'));
const table = decodeWords(new Uint8Array(readFileSync(join(dist, 'data', manifest.files.words.name))));
const words = new Set(Array.from({ length: table.count }, (_, i) => wordAt(table, i)));
const home = readFileSync(join(site, 'src/pages/index.astro'), 'utf8');
const examples = JSON.parse((/const EXAMPLES = (\[[^\]]*\])/.exec(home)?.[1] ?? '[]').replace(/'/g, '"'));
if (examples.length === 0) failures.push('index.astro: no EXAMPLES found');
for (const w of examples) if (!words.has(w)) failures.push(`index.astro: the example "${w}" is not on the list`);

if (failures.length) {
  console.error(`check-dist: ${failures.length} problem(s)`);
  for (const f of failures) console.error(`  - ${f}`);
  process.exit(1);
}
console.log(
  `check-dist: ${read} files read, CEOL_PUBLIC ${ceolPublic}, ${examples.length} examples on the list,` +
    ` ${runs.length} runs, ${masked.length} run words set aside; clean`,
);
