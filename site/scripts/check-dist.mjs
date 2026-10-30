// Checks the built site before it can be deployed. It fails when:
//   - CEOL_PUBLIC is false and a page or script names the CEOL Universe's
//     address, or the page about it exists;
//   - a public file carries a channel label the CEOL Universe withholds;
//   - a word the start page offers is no longer on the list.
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { decodeWords, wordAt } from '@eol/wordlist/decode';

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
// The labels as they appear in the list's own records and in the CEOL's files.
const WITHHELD = ['twl_scrabble_dictionary', 'tournament-list', 'collins', 'coca_frequency', 'merriam-webster', 'linux_', 'nltk_'];

let read = 0;
for (const path of files(dist)) {
  if (!TEXT.test(path)) continue;
  const rel = relative(dist, path);
  // the word lists are words, not labels: a withheld label's name can be a word
  if (rel.startsWith('downloads/')) continue;
  const text = readFileSync(path, 'utf8').toLowerCase();
  read++;
  if (!ceolPublic) for (const a of CEOL_ADDRESSES) if (text.includes(a)) failures.push(`${rel}: names ${a} while CEOL_PUBLIC is false`);
  if (rel.startsWith('data/')) for (const w of WITHHELD) if (text.includes(w)) failures.push(`${rel}: carries the withheld label ${w}`);
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
console.log(`check-dist: ${read} files read, CEOL_PUBLIC ${ceolPublic}, ${examples.length} examples on the list; clean`);
