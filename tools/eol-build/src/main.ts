import { writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { encodeWords, encodeMeta, INTAKE, INTAKE_NAMES, WordFlag } from '@eol/wordlist/format';
import { decodeWords, decodeMeta } from '@eol/wordlist/decode';
import { loadWords, loadWordSet } from './words.ts';
import { loadFacts } from './facts.ts';
import { emit, clearStale, kb, type Artifact } from './emit.ts';
import { writeDownloads } from './downloads.ts';
import { buildGrowth, buildStats } from './stats.ts';
import { buildProvenance, SHARD_COUNT } from './provenance.ts';
import { EXPECTED, check, assertExpectations } from './expected.ts';
import { DATA_DIR, INVALID_WORDS } from './paths.ts';

const decoder = new TextDecoder();

function step(n: number, label: string): void {
  process.stdout.write(`\n[${n}/6] ${label}\n`);
}

const started = Date.now();

// ---------------------------------------------------------------- 1. word list

step(1, 'Word list');
const words = await loadWords();
console.log(`      ${words.length.toLocaleString()} words`);
check('word count', words.length, EXPECTED.words);

const wordStrings = words.map((w) => decoder.decode(w));

// ------------------------------------------------------------- 2. provenance

step(2, 'Provenance (streaming merged_valid_dict.json, 291 MB)');
const facts = await loadFacts((seen) => {
  process.stdout.write(`      ${seen.toLocaleString()} entries\r`);
});
console.log(`      ${facts.size.toLocaleString()} entries read       `);

// ------------------------------------------------------- 3. cross-list check

step(3, 'Cross-checking against the invalid list (91 MB)');
const invalid = await loadWordSet(INVALID_WORDS);
console.log(`      ${invalid.size.toLocaleString()} invalid entries`);

const alsoInvalid: string[] = [];
for (const word of wordStrings) if (invalid.has(word)) alsoInvalid.push(word);
console.log(`      ${alsoInvalid.length} words appear in both lists`);
check('words in both lists', alsoInvalid.length, EXPECTED.alsoInvalid);

// ------------------------------------------------------------- 4. columns

step(4, 'Building columns');

const dates = new Set<string>();
for (const f of facts.values()) if (f.added) dates.add(f.added);
// Index 0 is reserved for "no date recorded", so the table is 1-based.
const dateTable = ['', ...[...dates].sort()];
const dateIndex = new Map(dateTable.map((d, i) => [d, i]));
if (dateTable.length > 0xffff) throw new Error(`${dateTable.length} distinct dates exceeds u16`);

const intake = new Uint8Array(words.length);
const added = new Uint16Array(words.length);
const flags = new Uint8Array(words.length);
const nonAlpha: boolean[] = new Array(words.length).fill(false);

const intakeCounts: Record<string, number> = { twl: 0, pipeline: 0, synthetic: 0, other: 0 };
let statusInvalidCount = 0;
let nonAlphaCount = 0;
let missingDate = 0;
let missingFacts = 0;
const dateCounts = new Map<string, number>();

for (let i = 0; i < words.length; i++) {
  const word = wordStrings[i]!;
  const fact = facts.get(word);
  let bits = 0;

  if (!fact) {
    // A word in the list with no entry in the dictionary. Counted rather than
    // guessed at: it means the two files disagree, which is worth reporting.
    missingFacts++;
    intake[i] = INTAKE.other;
    intakeCounts['other']!++;
  } else {
    intake[i] = INTAKE[fact.intake];
    intakeCounts[fact.intake]!++;
    if (fact.added) {
      added[i] = dateIndex.get(fact.added)!;
      dateCounts.set(fact.added, (dateCounts.get(fact.added) ?? 0) + 1);
    } else missingDate++;
    if (fact.statusInvalid) {
      bits |= WordFlag.StatusInvalid;
      statusInvalidCount++;
    }
  }

  if (invalid.has(word)) bits |= WordFlag.AlsoInvalid;

  for (const b of words[i]!) {
    if (b < 0x61 || b > 0x7a) {
      bits |= WordFlag.NonAlpha;
      nonAlpha[i] = true;
      nonAlphaCount++;
      break;
    }
  }

  flags[i] = bits;
}

for (const name of INTAKE_NAMES) {
  const count = intakeCounts[name]!;
  const share = count / words.length;
  console.log(`      ${name.padEnd(10)} ${count.toLocaleString().padStart(9)}  ${(share * 100).toFixed(2)}%`);
  check(`${name} share`, share, EXPECTED.intakeShare[name], `${count.toLocaleString()} words`);
}
console.log(`      status:invalid ${statusInvalidCount.toLocaleString()}`);
console.log(`      non-alphabetic ${nonAlphaCount.toLocaleString()}`);
console.log(`      no date        ${missingDate.toLocaleString()}`);
console.log(`      no dict entry  ${missingFacts.toLocaleString()}`);
console.log(`      distinct dates ${(dateTable.length - 1).toLocaleString()}`);

check('status:invalid entries', statusInvalidCount, EXPECTED.statusInvalid);
check('non-alphabetic words', nonAlphaCount, EXPECTED.nonAlpha);
check('words with no date', missingDate, EXPECTED.missingDate);
check('distinct dates', dateTable.length - 1, EXPECTED.distinctDates);

// The three bulk-load dates account for 98% of the list, so "sorted by date" is
// mostly one enormous tie. The interface says so rather than implying a
// timeline exists, and the figures it quotes come from here.
const bulk = [...dateCounts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3);
const bulkTotal = bulk.reduce((sum, [, count]) => sum + count, 0);
const individual = words.length - bulkTotal - missingDate;
console.log(
  `      bulk loads     ${bulkTotal.toLocaleString()} words on ${bulk.map(([d]) => d).join(', ')}` +
    ` (${((bulkTotal / words.length) * 100).toFixed(1)}%)`,
);
console.log(`      added singly   ${individual.toLocaleString()} words since the bulk loads`);

// ------------------------------------------------------------- 5. artifacts

step(5, 'Encoding artifacts');

const wordsBin = encodeWords(words);
const metaBin = encodeMeta(words.length, intake, added, flags);

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
  if (metaBack.intake[i] !== intake[i]) throw new Error(`round trip: intake at ${i}`);
  if (metaBack.added[i] !== added[i]) throw new Error(`round trip: added at ${i}`);
  if (metaBack.flags[i] !== flags[i]) throw new Error(`round trip: flags at ${i}`);
}
console.log('      round trip verified against every word');

const artifacts: Artifact[] = [
  await emit('words', 'bin', wordsBin),
  await emit('meta', 'bin', metaBin),
];

for (const a of artifacts) {
  const ratio = (a.bytes / a.brotliBytes).toFixed(2);
  console.log(`      ${a.name.padEnd(28)} ${kb(a.bytes).padStart(10)} → ${kb(a.brotliBytes).padStart(9)} brotli (${ratio}×)`);
}

const wire = artifacts.reduce((sum, a) => sum + a.brotliBytes, 0);
console.log(`      on the wire: ${wire.toLocaleString()} bytes (${kb(wire)})`);

// ------------------------------------------------------------- 6. manifest

step(6, 'Manifest');

const downloads = await writeDownloads(words, intake, nonAlpha);
for (const d of downloads) {
  console.log(`      ${d.file.padEnd(22)} ${d.words.toLocaleString().padStart(9)} words  ${kb(d.bytes).padStart(10)}`);
}

const growth = await buildGrowth();
const stats = buildStats(words, intake, growth);
const statsJson = `${JSON.stringify(stats)}\n`;
await writeFile(resolve(DATA_DIR, 'stats.json'), statsJson);
console.log(
  `      stats.json             ${kb(Buffer.byteLength(statsJson)).padStart(10)}` +
    `  ${stats.lengths.length} lengths, ${stats.growth.events.length} growth events`,
);
console.log(
  `      the list moved ${growth.last - growth.first} words across ${growth.daysRecorded} recorded days` +
    ` (${growth.recordedFrom} → ${growth.recordedTo})`,
);

const provenance = await buildProvenance((n) =>
  process.stdout.write(`      ${n.toLocaleString()} records\r`),
);
console.log(
  `      prov/ ${SHARD_COUNT} shards      ${kb(provenance.shardBytes).padStart(10)} total,` +
    ` ${kb(provenance.shardBytes / SHARD_COUNT)} average, ${kb(provenance.largestShard)} largest`,
);
console.log(
  `      ${provenance.written.toLocaleString()} words carry provenance` +
    ` · ${provenance.withDefinition} carry a real definition` +
    ` · ${provenance.sources.length} candidate sources`,
);

const manifest = {
  builtAt: new Date().toISOString(),
  provenance: {
    shards: SHARD_COUNT,
    sources: provenance.sources,
    manualSources: provenance.manualSources,
    llms: provenance.llms,
    categories: provenance.categories,
    statuses: provenance.statuses,
    words: provenance.written,
    withDefinition: provenance.withDefinition,
  },
  wordCount: words.length,
  dateTable,
  intakeCounts,
  statusInvalid: statusInvalidCount,
  alsoInvalid: alsoInvalid.length,
  alsoInvalidWords: alsoInvalid,
  nonAlpha: nonAlphaCount,
  bulkDates: bulk.map(([date, count]) => ({ date, count })),
  addedSingly: individual,
  downloads,
  files: Object.fromEntries(
    artifacts.map((a) => [a.key, { name: a.name, bytes: a.bytes, brotliBytes: a.brotliBytes }]),
  ),
};

await writeFile(resolve(DATA_DIR, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
const removed = await clearStale(artifacts, ['stats.json', 'prov']);
console.log(`      manifest.json written, ${removed} stale file${removed === 1 ? '' : 's'} removed`);

assertExpectations();

console.log(`\nDone in ${((Date.now() - started) / 1000).toFixed(1)}s\n`);
