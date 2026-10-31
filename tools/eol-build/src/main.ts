import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { encodeWords, encodeMeta, DECIDED, DECIDED_NAMES, WordFlag } from '@eol/wordlist/format';
import { decodeWords, decodeMeta } from '@eol/wordlist/decode';
import { loadWords, loadWordSet } from './words.ts';
import { INTAKE_NAMES, loadFacts, type Facts } from './facts.ts';
import { emit, clearStale, kb, type Artifact } from './emit.ts';
import { writeDownloads } from './downloads.ts';
import { buildGrowth, buildStats } from './stats.ts';
import { buildRecord } from './record.ts';
import { writeRuns } from './runs.ts';
import { EXPECTED, check, assertExpectations } from './expected.ts';
import { CACHE_DIR, DATA_DIR, INVALID_WORDS } from './paths.ts';

const decoder = new TextDecoder();

function step(n: number, label: string): void {
  process.stdout.write(`\n[${n}/6] ${label}\n`);
}

const started = Date.now();
const revision = (await readFile(resolve(CACHE_DIR, '.revision'), 'utf8').catch(() => '')).trim() || null;

// ---------------------------------------------------------------- 1. word list

step(1, 'Word list');
const words = await loadWords();
console.log(`      ${words.length.toLocaleString()} words`);
check('word count', words.length, EXPECTED.words);

const wordStrings = words.map((w) => decoder.decode(w));

// ------------------------------------------------------------- 2. the records

step(2, 'Records (streaming merged_valid_dict.json, 291 MB)');
const facts = await loadFacts((seen) => {
  process.stdout.write(`      ${seen.toLocaleString()} entries\r`);
});
console.log(`      ${facts.size.toLocaleString()} entries read       `);

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

const dates = new Set<string>();
for (const f of facts.values()) if (f.added) dates.add(f.added);
// Index 0 is reserved for "no date recorded", so the table is 1-based.
const dateTable = ['', ...[...dates].sort()];
const dateIndex = new Map(dateTable.map((d, i) => [d, i]));
if (dateTable.length > 0xffff) throw new Error(`${dateTable.length} distinct dates exceeds u16`);

const decided = new Uint8Array(words.length);
const added = new Uint16Array(words.length);
const flags = new Uint8Array(words.length);
const ordered: (Facts | undefined)[] = new Array(words.length);

// The intakes are counted for the tripwires below and never written out.
const intakeCounts: Record<string, number> = Object.fromEntries(INTAKE_NAMES.map((n) => [n, 0]));
let llmSaysInvalidCount = 0;
let nonAlphaCount = 0;
let missingDate = 0;
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
    intakeCounts['other']!++;
    decided[i] = DECIDED.none;
  } else {
    intakeCounts[fact.intake]!++;
    decided[i] = DECIDED[fact.decided];
    if (fact.added) {
      added[i] = dateIndex.get(fact.added)!;
      dateCounts.set(fact.added, (dateCounts.get(fact.added) ?? 0) + 1);
    } else missingDate++;
    if (fact.llmSaysInvalid) {
      bits |= WordFlag.LlmSaysInvalid;
      llmSaysInvalidCount++;
    }
  }

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

for (const name of INTAKE_NAMES) {
  const share = intakeCounts[name]! / words.length;
  check(`${name} share`, share, EXPECTED.intakeShare[name], `${(share * 100).toFixed(2)}%`);
}
const decidedCounts = Object.fromEntries(DECIDED_NAMES.map((n) => [n, 0])) as Record<string, number>;
for (const d of decided) decidedCounts[DECIDED_NAMES[d]!]!++;
for (const name of DECIDED_NAMES) {
  console.log(`      ${name.padEnd(15)} ${decidedCounts[name]!.toLocaleString().padStart(9)}`);
}
// The engine's words are exactly the synthetic intake's: the same field decides both.
check('engine words are the synthetic intake', decidedCounts['engine']! - intakeCounts['synthetic']!, { min: 0, max: 0 });

console.log(`      llm says invalid ${llmSaysInvalidCount.toLocaleString()}`);
console.log(`      non-alphabetic ${nonAlphaCount.toLocaleString()}`);
console.log(`      no date        ${missingDate.toLocaleString()}`);
console.log(`      no dict entry  ${missingFacts.toLocaleString()}`);
console.log(`      distinct dates ${(dateTable.length - 1).toLocaleString()}`);

check('entries an LLM called invalid', llmSaysInvalidCount, EXPECTED.llmSaysInvalid);
check('non-alphabetic words', nonAlphaCount, EXPECTED.nonAlpha);
check('words with no date', missingDate, EXPECTED.missingDate);
check('distinct dates', dateTable.length - 1, EXPECTED.distinctDates);

// The 3 bulk-load dates account for most of the list, so "sorted by date" is
// mostly 1 enormous tie. The interface says so rather than implying a timeline
// exists, and the figures it quotes come from here.
const bulk = [...dateCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3);
const bulkTotal = bulk.reduce((sum, [, count]) => sum + count, 0);
const individual = words.length - bulkTotal - missingDate;
console.log(`      bulk loads     ${bulkTotal.toLocaleString()} words on ${bulk.map(([d]) => d).join(', ')}`);
console.log(`      added singly   ${individual.toLocaleString()} words since the bulk loads`);

// ------------------------------------------------------------- 5. artifacts

step(5, 'Encoding artifacts');

const wordsBin = encodeWords(words);
const metaBin = encodeMeta(words.length, decided, added, flags);

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
  if (metaBack.decided[i] !== decided[i]) throw new Error(`round trip: decided at ${i}`);
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

const downloads = await writeDownloads(words, decided);
for (const d of downloads) {
  console.log(`      ${d.file.padEnd(22)} ${d.words.toLocaleString().padStart(9)} words  ${kb(d.bytes).padStart(10)}`);
}

const growth = await buildGrowth();
const { stats, unpublished } = buildStats(words, ordered, decided, growth);
await writeFile(resolve(DATA_DIR, 'stats.json'), `${JSON.stringify(stats)}\n`);
console.log(
  `      stats.json  ${stats.lengths.length} lengths, ${growth.points.length} recorded days` +
    ` (${growth.first.date} to ${growth.last.date}), ${growth.events.length} days with a change`,
);
console.log(
  `      channels: ${stats.channels.withPublished.toLocaleString()} words with a published channel,` +
    ` ${unpublished.withheld.toLocaleString()} withheld only, ${unpublished.unrecorded.toLocaleString()} unrecorded (not published)`,
);

const record = await buildRecord();
await writeFile(resolve(DATA_DIR, 'record.json'), `${JSON.stringify(record, null, 2)}\n`);
console.log(`      record.json  ${record.length} ledger lines`);

const manifest = {
  builtAt: new Date().toISOString(),
  revision,
  wordCount: words.length,
  dateTable,
  decidedCounts,
  llmSaysInvalid: llmSaysInvalidCount,
  invalidCount: invalid.size,
  alsoInvalid,
  nonAlpha: nonAlphaCount,
  missingDate,
  bulkDates: bulk.map(([date, count]) => ({ date, count })),
  addedSingly: individual,
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
console.log(`      runs.json  ${runs.length} runs, ${runWords} words dated a run's day, ${runMissing} named but not dated that day`);

assertExpectations();

console.log(`\nDone in ${((Date.now() - started) / 1000).toFixed(1)}s\n`);
