import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { encodeWords, encodeMeta, Attested, WordFlag } from '@eol/wordlist/format';
import { decodeWords, decodeMeta } from '@eol/wordlist/decode';
import { loadWords, loadWordSet } from './words.ts';
import { loadFacts, type Facts } from './facts.ts';
import { emit, clearStale, kb, type Artifact } from './emit.ts';
import { writeDownloads } from './downloads.ts';
import { buildGrowth, buildStats } from './stats.ts';
import { buildRecord } from './record.ts';
import { MOST_WORDS, writeRuns } from './runs.ts';
import { EXPECTED, check, assertExpectations } from './expected.ts';
import { CACHE_DIR, DATA_DIR, INVALID_WORDS } from './paths.ts';

const decoder = new TextDecoder();

function step(n: number, label: string): void {
  process.stdout.write(`\n[${n}/6] ${label}\n`);
}

const started = Date.now();
const revision = (await readFile(resolve(CACHE_DIR, '.revision'), 'utf8').catch(() => '')).trim() || null;
const publishedAt = (await readFile(resolve(CACHE_DIR, '.published'), 'utf8').catch(() => '')).trim() || null;

// ---------------------------------------------------------------- 1. word list

step(1, 'Word list');
const words = await loadWords();
console.log(`      ${words.length.toLocaleString()} words`);
check('word count', words.length, EXPECTED.words);

const wordStrings = words.map((w) => decoder.decode(w));

// ------------------------------------------------------------- 2. the records

step(2, 'Records (streaming merged_valid_dict.json)');
const { facts, unexpected, unexpectedRecords } = await loadFacts((seen) => {
  process.stdout.write(`      ${seen.toLocaleString()} entries\r`);
});
console.log(`      ${facts.size.toLocaleString()} entries read       `);
for (const [field, n] of unexpected) console.log(`      unexpected field ${field} on ${n.toLocaleString()} records`);
check('records with an unexpected field', unexpectedRecords, EXPECTED.unexpectedFields);

// ------------------------------------------------------- 3. cross-list check

step(3, 'Cross-checking against the invalid list (91 MB)');
const invalid = await loadWordSet(INVALID_WORDS);
console.log(`      ${invalid.size.toLocaleString()} invalid entries`);

let alsoInvalid = 0;
for (const word of wordStrings) if (invalid.has(word)) alsoInvalid++;
console.log(`      ${alsoInvalid} words appear in both lists`);
check('words in both lists', alsoInvalid, EXPECTED.alsoInvalid);

// ------------------------------------------------------------- 4. columns

step(4, 'Building columns');

// A date is kept only for a record that names a published intake.
const dates = new Set<string>();
for (const f of facts.values()) if (f.added && f.intake !== null) dates.add(f.added);
// Index 0 is reserved for "no date recorded", so the table is 1-based.
const dateTable = ['', ...[...dates].sort()];
const dateIndex = new Map(dateTable.map((d, i) => [d, i]));
if (dateTable.length > 0xffff) throw new Error(`${dateTable.length} distinct dates exceeds u16`);

const attested = new Uint8Array(words.length);
const added = new Uint16Array(words.length);
const flags = new Uint8Array(words.length);
const ordered: (Facts | undefined)[] = new Array(words.length);

let engineCount = 0;
let listedCount = 0;
let notChecked = 0;
let nonAlphaCount = 0;
let missingDate = 0;
let datedUnlabeled = 0;
let missingFacts = 0;
const dateCounts = new Map<string, number>();

for (let i = 0; i < words.length; i++) {
  const word = wordStrings[i]!;
  const fact = facts.get(word);
  ordered[i] = fact;
  let bits = 0;

  if (!fact) {
    // A word in the list with no entry in the dictionary. Counted rather than
    // guessed at: it means the 2 files disagree, which is worth reporting.
    missingFacts++;
    attested[i] = Attested.Unchecked;
    missingDate++;
  } else {
    attested[i] = fact.attested;
    if (fact.intake === 'synthetic_generation') {
      bits |= WordFlag.Engine;
      engineCount++;
    }
    if (fact.added && fact.intake !== null) {
      added[i] = dateIndex.get(fact.added)!;
      dateCounts.set(fact.added, (dateCounts.get(fact.added) ?? 0) + 1);
    } else {
      missingDate++;
      if (fact.added) datedUnlabeled++;
    }
  }

  if ((attested[i]! & Attested.Unchecked) !== 0) notChecked++;
  else if ((attested[i]! & Attested.Sources) !== 0) listedCount++;

  if (invalid.has(word)) bits |= WordFlag.AlsoInvalid;

  for (const b of words[i]!) {
    if (b < 0x61 || b > 0x7a) {
      bits |= WordFlag.NonAlpha;
      nonAlphaCount++;
      break;
    }
  }

  flags[i] = bits;
}

const engineShare = engineCount / words.length;
const listedShare = listedCount / words.length;
console.log(`      synthetic engine   ${engineCount.toLocaleString().padStart(9)}  ${(engineShare * 100).toFixed(2)}%`);
console.log(`      open source lists  ${listedCount.toLocaleString().padStart(9)}  ${(listedShare * 100).toFixed(2)}%`);
console.log(`      no open source     ${(words.length - listedCount - notChecked).toLocaleString().padStart(9)}`);
console.log(`      not checked yet    ${notChecked.toLocaleString().padStart(9)}`);
console.log(`      non-alphabetic     ${nonAlphaCount.toLocaleString().padStart(9)}`);
console.log(`      no date            ${missingDate.toLocaleString().padStart(9)}`);
console.log(`      dated, no source   ${datedUnlabeled.toLocaleString().padStart(9)}  (dates dropped)`);
console.log(`      no dict entry      ${missingFacts.toLocaleString().padStart(9)}`);
console.log(`      distinct dates     ${(dateTable.length - 1).toLocaleString().padStart(9)}`);

check('synthetic engine share', engineShare, EXPECTED.engineShare, `${(engineShare * 100).toFixed(2)}%`);
check('share at least 1 open source lists', listedShare, EXPECTED.attestedShare, `${(listedShare * 100).toFixed(2)}%`);
check('words not checked against the open sources', notChecked, EXPECTED.notChecked);
check('records dated without a published source', datedUnlabeled, EXPECTED.datedUnlabeled);
check('non-alphabetic words', nonAlphaCount, EXPECTED.nonAlpha);

// A day that dates more words than a night's run could add is a bulk load.
// The word panel says so rather than implying the words were found that day.
const bulk = [...dateCounts.entries()].filter(([, count]) => count > MOST_WORDS).sort((a, b) => a[0].localeCompare(b[0]));
const dated = words.length - missingDate;
console.log(`      bulk loads         ${bulk.map(([d, n]) => `${d} (${n.toLocaleString()})`).join(', ') || 'none'}`);

// ------------------------------------------------------------- 5. artifacts

step(5, 'Encoding artifacts');

const wordsBin = encodeWords(words);
const metaBin = encodeMeta(words.length, attested, added, flags);

// Round-trip before writing. An artifact that does not decode to what went in
// is worse than a failed build: it ships, and the interface quietly lies.
const table = decodeWords(wordsBin);
if (table.count !== words.length) throw new Error(`round trip: ${table.count} != ${words.length}`);
for (let i = 0; i < words.length; i++) {
  const start = table.offsets[i]!;
  const length = table.lengths[i]!;
  const original = words[i]!;
  if (length !== original.length) throw new Error(`round trip: length at ${i}`);
  for (let k = 0; k < length; k++) {
    if (table.bytes[start + k] !== original[k]) throw new Error(`round trip: bytes at ${i}`);
  }
}
const metaBack = decodeMeta(metaBin);
for (let i = 0; i < words.length; i++) {
  if (metaBack.attested[i] !== attested[i]) throw new Error(`round trip: attested at ${i}`);
  if (metaBack.added[i] !== added[i]) throw new Error(`round trip: added at ${i}`);
  if (metaBack.flags[i] !== flags[i]) throw new Error(`round trip: flags at ${i}`);
}
console.log('      round trip verified against every word');

const artifacts: Artifact[] = [await emit('words', 'bin', wordsBin), await emit('meta', 'bin', metaBin)];

for (const a of artifacts) {
  const ratio = (a.bytes / a.brotliBytes).toFixed(2);
  console.log(`      ${a.name.padEnd(28)} ${kb(a.bytes).padStart(10)} → ${kb(a.brotliBytes).padStart(9)} brotli (${ratio}×)`);
}

const wire = artifacts.reduce((sum, a) => sum + a.brotliBytes, 0);
console.log(`      on the wire: ${wire.toLocaleString()} bytes (${kb(wire)})`);

// ------------------------------------------------------------- 6. manifest

step(6, 'Manifest, statistics, record, and downloads');

const downloads = await writeDownloads(words, attested, flags);
for (const d of downloads) {
  console.log(`      ${d.file.padEnd(30)} ${d.words.toLocaleString().padStart(9)} words  ${kb(d.bytes).padStart(10)}`);
}

const growth = await buildGrowth();
const stats = buildStats(words, ordered, attested, flags, growth);
await writeFile(resolve(DATA_DIR, 'stats.json'), `${JSON.stringify(stats)}\n`);
console.log(
  `      stats.json  ${stats.lengths.length} lengths, ${growth.points.length} recorded days` +
    ` (${growth.first.date} to ${growth.last.date}), ${growth.events.length} days with a change`,
);
console.log(
  `      sources: ${stats.attestation.sources.map((s) => `${s.key} ${s.count.toLocaleString()}`).join(', ')}`,
);
console.log(
  `      intakes: ${stats.intakes.published.map((p) => `${p.source} ${p.count.toLocaleString()}`).join(', ')};` +
    ` no source ${stats.intakes.noSource.toLocaleString()}`,
);
if (stats.engine !== engineCount) throw new Error(`stats count ${stats.engine} engine words, the columns ${engineCount}`);

const record = await buildRecord();
await writeFile(resolve(DATA_DIR, 'record.json'), `${JSON.stringify(record, null, 2)}\n`);
console.log(`      record.json  ${record.length} ledger lines`);

const manifest = {
  builtAt: new Date().toISOString(),
  revision,
  publishedAt,
  wordCount: words.length,
  dateTable,
  engine: engineCount,
  invalidCount: invalid.size,
  alsoInvalid,
  nonAlpha: nonAlphaCount,
  dated,
  missingDate,
  bulkDates: bulk.map(([date, count]) => ({ date, count })),
  downloads,
  files: Object.fromEntries(
    artifacts.map((a) => [a.key, { name: a.name, bytes: a.bytes, brotliBytes: a.brotliBytes }]),
  ),
};

await writeFile(resolve(DATA_DIR, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
const removed = await clearStale(artifacts);
console.log(`      manifest.json written, ${removed} stale file${removed === 1 ? '' : 's'} removed`);

// The daily log reads the artifacts just written, so it comes last.
const runs = await writeRuns(growth);
const runWords = runs.reduce((n, r) => n + r.words.length, 0);
const runMissing = runs.reduce((n, r) => n + r.missing.length, 0);
console.log(`      runs.json  ${runs.length} runs, ${runWords} words added by a run, ${runMissing} named by a post but not counted`);

assertExpectations();

console.log(`\nDone in ${((Date.now() - started) / 1000).toFixed(1)}s\n`);
