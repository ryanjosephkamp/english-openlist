# Corrections

Every word this project moves between the valid and the invalid list is recorded
here first. The ledger is the source of truth; the word lists are regenerated
from it. A verdict can therefore be revisited without re-running anything, and
nothing moves without a recorded reason and a source you can go and check.

Until August 2026 the rule on this dataset was that no word is ever added,
removed or altered — documentation and infrastructure only. That was reversed
deliberately by the dataset's owner, not drifted away from. Promotion from the
invalid list to the valid list was always the nightly pipeline's job; what is
new is the ability to move a word the other way. Nothing has yet been moved that
way, and nothing will be without evidence recorded here.

## Ledger format

| Column | Meaning |
| --- | --- |
| `word` | the word |
| `stage` | which stage of the correction decided it |
| `verdict` | `valid` or `invalid` |
| `action` | what was done — currently only `remove_from_invalid_list` |
| `method` | how it was decided (see below) |
| `source` | the authority that ruled |
| `confidence` | `high`, `medium`, `low` |
| `evidence` | what that source actually left behind in the record |
| `part_of_speech` | as recorded by the source |
| `decided_date` | when |

`method` is the important column. `stored_api_ruling` means a dictionary API had
already ruled on the word and the ruling was sitting in the dataset. Any verdict
that ever comes from model judgement rather than a source will say so, so it can
be filtered or revisited later.

## Stage 1 — 150 dual-listed words, 13 August 2026

150 words were in `merged_valid_words.txt` **and** in the 9.2-million-entry
invalid list at the same time. A word must be one or the other.

None of them needed adjudicating. Every one already carried a dictionary ruling
inside its own record in `merged_valid_dict.json`:

| | |
| --- | ---: |
| Ruled by Free Dictionary | 86 |
| Ruled by Merriam-Webster | 63 |
| Ruled by Merriam-Webster Medical | 1 |
| Carrying the full raw API response | 139 |
| Carrying a definition | 149 |
| Carrying a part of speech | 150 |
| Passing `word_validator`'s Scrabble rules | 150 |
| Flagged by Merriam-Webster as an abbreviation | 0 |

They are words like `mpox`, `sertraline`, `capicola`, `arancini`, `hashtag`,
`unfollow`, `doomscrolling` and `chupacabra` — real, recent, correctly promoted.
What went wrong is that they were added to the valid list without being removed
from the invalid one.

So all 150 were cleared as valid and removed from the invalid list. **None was
demoted, and the valid list was not touched.** The stage cost no dictionary API
calls at all, because the evidence was already in the file.

| | Before | After |
| --- | ---: | ---: |
| `merged_valid_words.txt` | 378,891 | 378,891 |
| `merged_invalid_words.txt` | 9,275,411 | 9,275,261 |
| words in both lists | 150 | **0** |

Separately, 201 entries carried `"status": "WordStatus.VALID"` — a Python enum
stringified by a writer that has since been replaced. Those were normalised to
`"valid"`. A line-by-line comparison against the pre-change file found exactly
201 differing lines, all of that one shape, and nothing else.

The build now asserts that no word is in both lists, as an exact zero rather
than a range. If it ever fails, the promotion path in
`scripts/validate_invalid_list.py` has regressed, and widening the bound is the
wrong fix.

### Spot-check

The verdicts rest on rulings recorded in December 2025 – May 2026, so a sample
was re-checked live on 13 August 2026 against the Free Dictionary API — the same
source that ruled on 86 of them, and one that costs no Merriam-Webster quota.

Five of the most obscure Free-Dictionary-sourced words all still return an entry:

| Word | Live result |
| --- | --- |
| `bockety` | adjective — unsteady, wobbly, rickety |
| `cheeselog` | noun — a woodlouse |
| `deurmekaar` | adjective — mixed up, heterogeneous |
| `baggywrinkle` | noun — a rope pad attached to a shroud |
| `skedonk` | noun — an old, battered motor car |

The 63 Merriam-Webster-sourced words could not be independently corroborated
this way: Free Dictionary has none of them, which is why MW ruled on them in the
first place. Their evidence is the stored MW response, which carries the
collegiate source and entry UUID. That is worth knowing when reading the
`high` confidence on those rows — it is one source, recorded, not two agreeing.

### Reproducing it

    python scripts/build_correction_ledger.py --data-dir .cache/hf --out corrections
    python scripts/apply_correction_ledger.py --data-dir .cache/hf \
        --ledger corrections/ledger_stage1.csv --dry-run

The applier refuses any action it does not recognise, and refuses to remove a
word from the invalid list unless that word is in the valid list — that would be
deleting a word rather than correcting one. It is idempotent, so re-running it
against already-corrected data changes nothing.

The state immediately before this change is preserved in two places: the
`stage1-backup-2026-08-13` branch of the private `eol-archive` repository, and
`~/Documents/english-openlist-prune-mirror/stage1-backup-2026-08-13`. Both were
verified to decompress byte-identical before anything was written. Hugging Face
keeps no history to fall back on.

## Stage 2 — measuring the LLM verdict, August 2026

20,052 words in the valid list carry `"status": "invalid"`. Every one of those
verdicts came from a single pass by **Google Gemini 3 Flash Preview** in
December 2025 — a pass that also marked 117,653 other words *valid*. The
pipeline's own deterministic checks passed 97.8% of them, and `abacavir`, an HIV
antiretroviral attested in COCA, Google Ngrams, Wikipedia and Wiktionary, is
among the supposedly invalid.

**No word moves in this stage.** It measures how often that pass was wrong, so
the decision about the other 19,652 rests on evidence rather than on the field's
say-so. Every ledger row carries `action: none`.

### What is being measured, and what cannot be

The result is a **lower bound**. A dictionary having the word proves the LLM
wrong; a dictionary *not* having it proves nothing, because much of this
vocabulary is technical and absence from Merriam-Webster is not absence from
English. Four outcomes, and only the first two enter the rate:

| Outcome | Meaning |
| --- | --- |
| `refuted` | a source returns `valid` — the LLM was wrong |
| `corroborated` | a source returns `abbreviation` or `proper_noun`, both of which this dataset excludes — the LLM's call was defensible |
| `unadjudicated` | no source has an entry — nothing follows |
| `error` | every source failed — excluded from the rate, counted separately |

An error is never read as a verdict. That distinction matters because
`validate_invalid_list.py` does not make it: its `else` branch sweeps `ERROR` in
with the rejections, so a rate-limited lookup already reads as "not a word" in
the nightly pipeline.

### The sample

400 words, stratified by how many corpora attested them — a word with four
independent corpora behind it is a different case from one with none, and
pooling them would hide exactly the pattern worth finding.

| Stratum | Population | Sampled | Rate |
| --- | ---: | ---: | ---: |
| 0 corpus sources | 448 | 40 | 8.9% |
| 1 source | 10,056 | 160 | 1.6% |
| 2 sources | 4,906 | 80 | 1.6% |
| 3 sources | 2,254 | 60 | 2.7% |
| 4+ sources | 2,388 | 60 | 2.5% |
| **Total** | **20,052** | **400** | **2.0%** |

Stratum 0 is oversampled deliberately: it holds only 448 words but is the most
likely place for the LLM to have been right, and a proportional draw would say
nothing about it. It also mixes two different claims — 307 words whose sources
*all* said "unlikely", and 141 with no sources at all — so `all_unlikely` is
recorded per row and the split can be analysed without drawing again.

`stage2_frame.csv` and `stage2_sample.csv` are **committed before any lookup
runs**. A sample chosen after seeing results is not a sample, and a reader would
have no way to tell afterwards. The workflow redraws the sample from the
recorded seed and fails if the committed file differs. Selection ranks each word
by `sha256(seed:stratum:word)` rather than `random.sample`, whose internals are
free to change between Python releases — anyone can recompute it in any
language.

### How the rate is computed

- **Per stratum**: `refuted / (refuted + corroborated)` with a **Wilson score**
  95% interval, used rather than the normal approximation because the
  denominators are small and the proportions may sit near 0 or 1, where the
  textbook interval reports impossible bounds.
- **Overall**: population-weighted, `Σ (N_h/N)·r_h`. Pooling the raw counts
  would let stratum 0 — sampled at 8.9% against 1.6% — dominate a figure meant
  to describe all 20,052 words. The variance carries the finite population
  correction, since 40 of 448 is not a draw from an infinite population.
- **Twice over**: Free Dictionary performs no abbreviation or proper-noun
  screening, so every figure is also given counting only Merriam-Webster
  rulings.

### Running it

`.github/workflows/stage2_sample.yml`, triggered by hand. It runs in Actions
rather than on a laptop because a ruling with a public log and a timestamp is
defensible to a stranger, and because that is where the API keys live.

Sources are consulted **Medical, then Collegiate, then Free Dictionary**.
Medical leads because its quota is unspent while the nightly consumes
Collegiate's entirely, and because this vocabulary is heavily medical and
chemical.

Responses are cached under `.cache/dictionary/` so a re-run costs nothing —
verified: a warm cache makes **0** outbound calls. The cache is off unless
`EOL_DICT_CACHE` is set, so the nightly's behaviour is unchanged; a stale cached
"not found" would otherwise freeze a word out of promotion indefinitely. Errors
are never cached, since a 429 is a statement about our quota rather than about
the word.

### The result: the method cannot answer the question

Run on 2026-08-14. **The stop rule fired.**

| | |
| --- | ---: |
| Words sampled | 400 |
| Answered by MW Collegiate or MW Medical | **400 of 400** |
| **Absent from both MW dictionaries** | **383 (95.8%)** |
| Adjudicable at all | **18 (4.5%)** |
| Of those: LLM refuted | 13 |
| Of those: LLM corroborated | 5 |

The measurement it produces — a weighted error rate of ~81% with a 95% interval
of 63% to 99% — **rests on 18 words and is not fit to decide anything about
20,052.** Reporting it as the answer would be the kind of number that looks like
evidence and is not.

**What the run does establish, firmly, is something more useful:**

> Merriam-Webster has no entry for 95.8% of set B. Collegiate and Medical
> between them answered every single word, and for 383 of 400 the answer was
> "no such headword".

That kills the option of adjudicating set B exhaustively. Spending ~20 days of
API budget on all 20,052 words would return "no entry" for roughly 19,200 of
them. The vocabulary is simply outside what these dictionaries cover, and no
amount of budget changes that.

Where MW *could* rule, the LLM was wrong on **13 of 18**. The five it got right
were all proper nouns — `christmastides`, `elzevir`, `mishnaic`, `taiwanese`,
`talmudist` — which is a category it handled, not general competence. Among the
words it wrongly rejected: `clorazepate` (a benzodiazepine), `antinociceptive`,
`hemoconcentrations`, `esophagogastroplasty`, `rotifera`, `palliasse`.

Two caveats recorded honestly:

- **Free Dictionary was effectively down**, erroring on 338 of 383 lookups and
  still on 298 after a retry. It contributed one ruling. Since it performs no
  proper-noun screening, and stratum 0 is full of taxonomic names like
  `acidobacteriota` and `carcinonemertidae`, its rulings would have been weak
  evidence for exactly the words in question.
- **The quota premise behind this stage was wrong.** `DAILY_VALIDATION_LIMIT`
  was lowered to 600 to free Collegiate budget, on the assumption that a full
  nightly run exhausts the 1000/day limit. Hours after a full run, Collegiate
  answered 393 of 393 and Medical 400 of 400, none rate-limited. The limit is
  back at 1000 and no borrowing was needed.

The re-run cost **zero** Merriam-Webster calls — 393 Collegiate and 400 Medical
cache hits, no misses — which is the cache working as intended.

### The decision: relabel, move nothing

Taken 2026-08-14. **No word in set B was moved, and none will be on this
evidence.** Not because the LLM was reliable — where a dictionary could check
it, it was wrong more often than right — but because 95.8% of the set cannot be
adjudicated by any source this project has. A demotion nobody can defend is
worse than an honest label.

So the field was renamed to carry its own warning:

| Old | New | Entries | What it actually is |
| --- | --- | ---: | --- |
| `status` | `unverified_llm_verdict` | 137,705 | one LLM pass, Gemini 3 Flash Preview, Dec 2025 |
| `status` | `dictionary_verdict` | 201 | a real Merriam-Webster or Free Dictionary ruling, via the promotion path |

**The split is the point.** `status` looked like one field and was two. Those 201
entries came through the promotion path and their verdict is a dictionary's, not
a machine's — labelling them "unverified LLM" would have been a fresh error in
the opposite direction. They are separable without guessing: an LLM-sourced
verdict always carries a `manual_validation` block, and those 201 carry none.

The raw verdict and its full provenance are untouched. Nothing was deleted;
`manual_validation` still records the model, the date and the revalidation
thread. Only the name changed, so that reading the data no longer requires
reading this file first.

Applied by `scripts/relabel_llm_verdict.py`, which renames the key **in place**
rather than removing and re-adding it. That detail is not cosmetic: popping the
key appends the new one at the end of the entry, which is invisible in the
parsed data and turns a one-key rename into a 6.9-million-line diff on a 291 MB
published file. Renaming in place kept it to the 137,906 lines that genuinely
changed, verified by a line-by-line comparison against the pre-change backup —
three distinct diff shapes, all of them the rename.

## Stage 3 — the synthetic comparatives, August 2026

16,478 of the 64,837 synthetic words are comparatives and superlatives:
`abacteremicer`, `abambulacralest`, `abatabler`. Like the rest of that intake
they carry no attestation of any kind while being marked `validated: true`.

**Asked the right way round.** Merriam-Webster will never carry `abacteremicer`
as a headword, so looking up the form would return "not found" 8,809 times and
prove nothing. Instead the *stem* is looked up and its `meta.stems` array read —
the list of inflections MW recognises for that headword, and the same array
`_entry_matches_word` already uses to resolve plurals. A "no" there is the
dictionary enumerating a word's forms and leaving this one out, which is far
stronger than a failed headword lookup. It also gives leverage: 16,478 forms
reduce to 8,809 stems.

### Coverage — unlike stage 2, this question can be answered

| Stratum | Stems | Sampled | MW ruled | Coverage |
| --- | ---: | ---: | ---: | ---: |
| WordNet adjective | 1,717 | 100 | 94 | 94.0% |
| WordNet noun/verb only | 306 | 50 | 46 | 92.0% |
| Not in WordNet | 6,786 | 150 | 43 | 28.7% |
| **Total** | **8,809** | **300** | **183** | **61.0%** |

Stage 2 could rule on 4.5% of its sample and was stopped on that basis. This one
reaches 61%, so the result below is worth something.

### The result

**Of 183 stems Merriam-Webster could rule on, it recognises the comparative for
exactly one** — 0.5%, 95% CI 0.1–3.0%.

| Stratum | MW ruled | Recognised | Not recognised |
| --- | ---: | ---: | ---: |
| WordNet adjective | 94 | 1 | 93 |
| WordNet noun/verb only | 46 | 0 | 46 |
| Not in WordNet | 43 | 0 | 43 |

Weighted by each stratum's share of the 8,809 stems: **0.21%**, on the order of
18 stems and perhaps 34 of the 16,478 forms that a dictionary would accept.

The one it got right is `blameworthy` → `blameworthier`, `blameworthiest`. A
real gradable adjective, produced by the same blind affixation that produced
`abominabler`, `affabler` and `ahistoricaler`. The generator was not right on
purpose.

The evidence is direct rather than inferred. MW lists `kiss kissable kissed
kisses kissing` for `kissable` and `breathabilities breathability breathable`
for `breathable` — full inflection sets, with `kissabler` and `breathabler`
simply not among them.

**Caveat, stated rather than buried:** the extrapolation to the full 8,809
assumes unrulable stems behave like rulable ones within their stratum. That is
least safe for *not in WordNet*, at 28.7% coverage — but those are also the most
obscure stems, so if the assumption fails it most likely flatters the generator.

**Nothing has been moved.** Stage 3 measures; what to do about the cluster is a
separate decision.

## Not yet decided

- **The 16,478 `-er`/`-est` synthetic forms.** The evidence now says ~99.8% of
  them are not English. Demoting them is the first genuine *valid → invalid*
  move this project would make, and that is Ryan's call, not a measurement's.
- **The other 48,359 synthetic words** — plurals, `-ed`/`-ing` forms and
  prefixed constructions — are unmeasured. The same stem-and-`meta.stems`
  method would work on them.
- **64,837 synthetic words carry no attestation of any kind** — no corpus source,
  no validation record — while marked `validated: true` and noted as "awaiting
  validation". 95.9% are derived forms of stems already in the list, and 16,478
  of them are comparatives and superlatives on adjectives that cannot take them.
