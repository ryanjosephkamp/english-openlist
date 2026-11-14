---
annotations_creators:
  - machine-generated
  - expert-generated
language:
  - en
language_creators:
  - found
license: other
license_name: mixed
license_link: https://huggingface.co/datasets/ryanjosephkamp/english-openlist#license
multilinguality:
  - monolingual
pretty_name: English OpenList
size_categories:
  - 100K<n<1M
source_datasets:
  - original
tags:
  - dictionary
  - word-list
  - lexicography
  - nlp
  - spell-checking
task_categories:
  - text-classification
task_ids:
  - text-classification-other-word-validation
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/merged_valid_words.txt
---

# English OpenList

**A large, free, validated English word list for NLP and games.**

## Dataset Description

English OpenList is a continuously updated dictionary of valid English words. It provides:

- **~345,000 validated English words**, plus a candidate pool of ~9.3 million awaiting evidence
- **Open attestation** for every word: which openly licensed sources list it
- **Daily updates** from authoritative dictionary sources
- **Version history** with changelogs for every update

> **What the metadata is.** `merged_valid_dict.json` records, for each word, which
> openly licensed sources list it, and for some words how and when they came in.
> It does **not** contain definitions, parts of speech, pronunciations, or
> frequency data. If you need those, pair this list with WordNet or Wiktionary.

### Why Use English OpenList?

| Use Case | Benefit |
|----------|---------|
| **Spell Checking** | High-precision word validation |
| **Word Games** | Wordle-style out of the box; word-game files by length are in `latest/brrrdle/` |
| **NLP Training** | Clean, validated vocabulary |
| **Research** | Transparent methodology, open attestation per word |

## Dataset Structure

### Full Word Lists (data/)

**These are the complete, up-to-date word lists that most users will want to download:**

```
data/
├── merged_valid_words.txt      # FULL valid word list (~345,000 words, one per line)
├── merged_valid_dict.json      # FULL dictionary: each word's open attestation
├── merged_invalid_words.txt    # FULL invalid/rejected entries list
└── merged_invalid_dict.json    # FULL invalid dictionary with rejection reasons
NOTICES.md                      # the notices and licenses of the attesting sources
```

### Daily Releases (releases/)

Daily updates with changelog and statistics:

```
releases/
└── {YYYY-MM-DD}/
    ├── update_stats.json       # Statistics for the update, including the
    │                           # `promoted_words` and `new_words` lists
    └── CHANGELOG.md            # Changelog for the update
```

A release folder is the record of what changed that day, not a second copy of
the dataset — the complete lists are in `data/`, and the current snapshot is in
`latest/`.

### Latest Update Reference (latest/)

The most recent release, plus a copy of the current full lists, for convenience:

```
latest/
├── merged_valid_words.txt
├── merged_valid_dict.json
├── update_stats.json
└── CHANGELOG.md
```

### Brrrdle Artifacts

Brrrdle-compatible artifacts are generated during daily automation and uploaded to:

```
latest/brrrdle/
data/brrrdle/
```

The primary Brrrdle files are `words_length_{N}.json` for every supported length
from 2 through 35. Each file contains `metadata.curation`, curated `answers`, and
complete `validGuesses`. The `validGuesses` array remains the full per-length
list, while `answers` is generated with the deterministic
`stratified_quality_score_v1` method using seed `42 + length`. Both arrays contain
plain word strings.

During the transition to length-specific artifacts, the legacy length-5
compatibility files `brrrdle_words.txt` and `brrrdle_words.json` are still
published. These legacy files should be removed in the next major Brrrdle
artifact update, along with any legacy-only manifest or generated README behavior.

### Data Fields

Every record in `merged_valid_dict.json` has the same fields. The object's keys
are the words, in sorted order.

| Field | Always there | What it holds |
|---|---|---|
| `word` | yes | The word, the same as its key. |
| `length` | yes | Its length in characters. |
| `attested_by` | yes, except words added since the last attestation pass | The openly licensed sources whose own files list the word, in a fixed order: `wiktionary`, `wordnet`, `scowl`, `libreoffice`, `enable`, `wordfreq`. An empty list means none of them lists it. |
| `source` | no | How the word came in, for 5 intakes: `synthetic_generation` (the synthetic engine), `authoritative_extracts` and `extended_domain_sources` (glossaries of fields such as medicine), `free-dictionary` (the Free Dictionary API), and `invalid_list_recovery` (the nightly run's promotions). |
| `added_date` | no | The day the word came in, `YYYY-MM-DD`, on records that carry a `source`. |

```json
{
  "word": "broth",
  "length": 5,
  "attested_by": ["wiktionary", "wordnet", "scowl", "libreoffice", "enable", "wordfreq"]
}
```

```json
{
  "word": "abacavirs",
  "length": 9,
  "attested_by": [],
  "source": "synthetic_generation",
  "added_date": "2026-01-11"
}
```

A record with no `source` came in with the list's first build, in December 2025
and January 2026: from a discovery pipeline over open sources, or from word lists
whose terms don't allow this dataset to say which words they supplied. The
record doesn't say which, by design. `attested_by` is what each of those words
can be checked against.

`attested_by` is filled by an attestation pass run against pinned copies of the
sources (`scripts/open_attestation.py` in the source repository). A word counts
as listed when the source's file holds exactly that string; for WordNet, a word
also counts when WordNet's own morphology maps it to a lemma. Words the nightly
run promotes carry no `attested_by` until the next pass. `NOTICES.md` carries
each source's notice and license.

### Validation Rules: any length

**The form rule is `^[a-z]+$` with no length limit.** Until August 16, 2026, the
list carried a 2-character minimum and a 45-character maximum. Both were removed
because both excluded real English:

- the minimum excluded **`a`** and **`i`**;
- the maximum excluded **`phosphoribosylaminoimidazolesuccinocarboxamide`**, 46
  characters, which carries a Wiktionary English entry. Chemical nomenclature is
  productive and unbounded, so any ceiling is arbitrary.

**If you need those bounds, use the site's `lengths-2-to-45.txt` download**, which
applies them.

Rules applied to **newly discovered words** by the daily pipeline:

- ✅ Contain only lowercase letters (a-z), any length
- ✅ Are recognized by a dictionary API
- ❌ Are NOT proper nouns (unless commonly used as verbs)
- ❌ Are NOT abbreviations or acronyms

Words already in the list arrived through earlier intakes and were not all
checked against a dictionary — see *Composition* below. Lengths run from 1 to
47 characters (`a` at one end, `phosphoribosylaminoimidazolesuccinocarboxamides`
at the other).

**One further note on the two files.** `merged_invalid_words.txt` is *not* a list
of non-words. It is the pool of candidate strings that have not yet been
validated, and words move out of it into the valid list every night. Read it as
"not yet confirmed", never as "rejected".

## Dataset Statistics

| Metric | Value |
|--------|-------|
| Total Valid Words | ~345,000 (grows daily) |
| Total Invalid Entries | 9,275,000+ |
| Update Frequency | Daily (00:00 UTC) |
| Sources for New Words | Merriam-Webster's and Wordnik's words of the day, and manual additions |

Counts here are approximate by design — the list grows every day. For the exact
current figure see [`latest/update_stats.json`](https://huggingface.co/datasets/ryanjosephkamp/english-openlist/blob/main/latest/update_stats.json).

### Composition

The list came in through several intakes over time, and they are not
interchangeable. Anyone filtering or scoring this data should know the mix
(344,830 words when the attestation pass ran):

| Group | Words | How to identify |
|--------|------:|-----------------|
| The first build | 312,944 | no `source` |
| The synthetic engine | 31,243 | `source: "synthetic_generation"` |
| Glossaries, the Free Dictionary API, and the nightly run | 643 | the other 4 `source` values |

And by open attestation, a word counting under each source that lists it:

| Source | Words that it lists |
|--------|------:|
| Wiktionary | 254,765 |
| SCOWL | 204,041 |
| ENABLE | 169,639 |
| LibreOffice dictionaries | 124,397 |
| WordNet | 111,382 |
| wordfreq | 100,462 |
| **At least 1 of them** | **268,762** |
| None of them | 76,068 |

The synthetic group contains algorithmically constructed forms such as
`abacteremicer` and `nonlivabler`. They are kept deliberately — this list aims
to be broad, and removing them would narrow it — but they are the group most
likely to surprise you. Applications wanting only conventional vocabulary should
filter on `source`, on `attested_by`, or on both.

## Usage

### Python (Hugging Face Datasets)

The default configuration is the valid word list, one word per row in a `text`
column:

```python
from datasets import load_dataset

dataset = load_dataset("ryanjosephkamp/english-openlist", split="train")

for entry in dataset:
    print(entry["text"])
```

Every other file in the repository — the metadata dictionary, the daily releases,
the Brrrdle artifacts — remains browsable and downloadable; they are simply not
part of the default load. Point at one explicitly to read it:

```python
dataset = load_dataset(
    "ryanjosephkamp/english-openlist",
    data_files="releases/2026-08-11/merged_valid_words.txt",
    split="train",
)
```

Or fetch the file directly, which is usually what you want for a word list:

```python
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    "ryanjosephkamp/english-openlist",
    "data/merged_valid_words.txt",
    repo_type="dataset",
)
words = set(open(path).read().split())
print("hello" in words)   # True
```

### Direct Download

**Download the complete word lists:**

```bash
# Download the FULL valid word list
wget https://huggingface.co/datasets/ryanjosephkamp/english-openlist/resolve/main/data/merged_valid_words.txt

# Download FULL valid dictionary with metadata
wget https://huggingface.co/datasets/ryanjosephkamp/english-openlist/resolve/main/data/merged_valid_dict.json

# Download FULL invalid words list (for reference)
wget https://huggingface.co/datasets/ryanjosephkamp/english-openlist/resolve/main/data/merged_invalid_words.txt

# Download FULL invalid dictionary
wget https://huggingface.co/datasets/ryanjosephkamp/english-openlist/resolve/main/data/merged_invalid_dict.json
```

**Download daily release files:**

```bash
# Download a specific day's update
wget https://huggingface.co/datasets/ryanjosephkamp/english-openlist/resolve/main/releases/2026-01-19/CHANGELOG.md
```

### Python (Raw Files)

```python
import json

# Load word list
with open("merged_valid_words.txt", "r") as f:
    words = set(line.strip() for line in f)

# Check if a word is valid
print("hello" in words)  # True
print("asdf" in words)   # False

# Load the dictionary for each word's open attestation.
with open("merged_valid_dict.json", "r") as f:
    dictionary = json.load(f)

entry = dictionary["broth"]
print(entry["attested_by"])     # ['wiktionary', 'wordnet', 'scowl', ...]
print(entry.get("source"))      # None: a first-build word

# Only the words at least 1 open source lists
listed = [w for w, e in dictionary.items() if e.get("attested_by")]
```

## Methodology

### Phase 1: Corpus Acquisition (December 2025)

Aggregated 9.8 million candidate words from 15+ sources, among them:
- Wiktionary (6.5M words)
- WordNet 3.1 (150K words)
- SCOWL 2020 (500K words)
- Google Books Ngrams (1M+ words)

### Phase 2: Validation Pipeline (December 2025 - January 2026)

Validation in several stages:
- Pattern-based screening
- A language-model pass over the candidates (its verdicts are no longer in the records; see Phase 4)
- Statistical sampling for quality assurance
- Synthetic word generation and validation

### Phase 3: Continuous Updates (January 2026 - Ongoing)

Daily automated pipeline:
1. Discover new words from Merriam-Webster RSS feed and manual additions
2. Validate ~1,000 words from invalid list against dictionary APIs
3. Promote validated words to the valid list
4. Update full word lists and dictionaries on Hugging Face
5. Generate changelog and statistics

### Phase 4: Correcting the list itself (August 2026 - Ongoing)

Until August 2026 this dataset was only ever added to. Words are now also
corrected, with every decision recorded in
[`corrections/`](https://github.com/ryanjosephkamp/english-openlist/tree/main/corrections)
in the source repository before any list is rewritten.

**August 13, 2026.** 150 words were in `merged_valid_words.txt` and in
`merged_invalid_words.txt` at the same time — words the daily pipeline had
promoted onto one side without removing them from the other. Every one already
carried a dictionary API ruling in its own record (a withheld dictionary for 64,
Free Dictionary for 86), so all 150 were cleared as valid and
removed from the invalid list. **None was demoted, and the valid word list did
not change.** 201 entries whose `status` field (now `dictionary_verdict`) read `"WordStatus.VALID"` — a
stringified Python enum — were normalized to `"valid"` in the same change.

**August 14, 2026 — the `status` field was renamed, and measured.**

`status` read like this dataset's verdict on a word. It was not: on 137,705
entries it recorded what one LLM pass (Google Gemini 3 Flash Preview, December
2025) thought. It was renamed `unverified_llm_verdict`, so nobody had to read the
documentation to find that out. The records no longer carry it (November 2026,
below).

Before deciding what to do about the 20,052 words it calls invalid, its accuracy
was measured. 400 were sampled, stratified by how many corpora attested them,
and looked up in Merriam-Webster Collegiate and Medical:

| | |
|---|---:|
| Sampled | 400 |
| **Absent from Merriam-Webster entirely** | **383 (95.8%)** |
| Could be checked at all | 18 |
| Of those, the LLM was wrong | 13 |
| Of those, the LLM was right | 5 (all proper nouns) |

Words it wrongly rejected include `clorazepate`, `antinociceptive`,
`hemoconcentrations`, `esophagogastroplasty`, `rotifera` and `palliasse`.

**No word was moved, and none can be.** Merriam-Webster answered every word we
asked and had no entry for 95.8% of them — this vocabulary is chemical, medical
and taxonomic, outside what these dictionaries cover. Adjudicating all 20,052
would return "no entry" for roughly 19,200 of them at any budget. So the verdict
is kept with its provenance and clearly labeled, rather than acted on or
quietly deleted.

**August 14, 2026 — 33,594 synthetic forms were demoted.**

The word count fell from 378,891 to **345,297**. This is the first time words
have ever left the valid list, and it was done on measured evidence.

They were forms built by blind affixation, in two groups:

| Group | Forms | MW ruled on | MW accepted |
| --- | ---: | ---: | ---: |
| comparatives and superlatives | 16,476 | 183 stems | 1 |
| plural gerunds, verb forms, agent plurals | 17,118 | 109 stems | 0 |

Merriam-Webster was asked by reading the inflections it records for each stem
(`meta.stems`) rather than looking the invented form up as a headword, which MW
would never carry. It lists `advert adverted adverting adverts` and has no
`advertings`.

Everything MW accepted was kept: `blameworthier`, `blameworthiest`, and four
plurals.

**These words were moved, not deleted, and none of them is marked permanently
invalid.** A demotion here means no dictionary we could reach recognized the
word on that date — not that it is not a word. Every demoted word is in a
recheck queue that the daily pipeline draws from on a reserved part of each
night, bypassing the length filter that would otherwise hide the longer ones
indefinitely. Each one names its reason in
[`corrections/ledger_demotions.csv`](https://github.com/ryanjosephkamp/english-openlist/tree/main/corrections).

**November 2026 — every word checked against open sources, and one record shape.**

Every word was checked against 6 openly licensed sources (Wiktionary, WordNet,
SCOWL, the LibreOffice dictionaries, ENABLE, and wordfreq), and each record now
names the ones that list it in `attested_by`. Every record was reduced to the
same few fields: the records no longer carry the first build's discovery log,
the verification pipeline's working fields, the language model's verdicts, or
dates for first-build words.

**332 words left the list**: no open source lists them, and the list's record of
where they came from can't be published. The count went from 345,162 to
344,830.

Two known issues remain, **deliberately not acted on**:

- **20,048 first-build words were called invalid by the language-model
  pass and stayed on the list.** Where a dictionary could check, that pass was
  wrong more often than right, so nothing was moved on its word. The records no
  longer say which words they are; about half of them (10,298 of 20,048) are
  listed by none of the 6 open sources.
- **29,126 of the 31,243 synthetic words are listed by none of the 6 open
  sources.**

  **These were deliberately kept, not overlooked.** Most are plurals, and when
  Merriam-Webster was asked about those it could rule on only 9.2% of their
  stems — but accepted four of the eleven it could: `bioterrorisms`,
  `defamiliarizations`, `ebullisms`, `ferroelectricities`. Demoting a group on
  that evidence would have discarded real words. Settling them needs a source
  that covers technical nouns, which Merriam-Webster does not.

  If you need only words an open source lists, filter on `attested_by`.

## Citation

```bibtex
@dataset{english_openlist_2026,
  title = {English OpenList: A Comprehensive Validated English Word List},
  author = {Kamp, Ryan},
  year = {2026},
  publisher = {Hugging Face},
  url = {https://huggingface.co/datasets/ryanjosephkamp/english-openlist}
}
```

## What the records leave out

The records say which open sources list a word, and for some words how and when
they came in. They don't record the first build's discovery log or working
fields, and they don't name sources whose terms don't allow it. No record holds
a dictionary's definition, pronunciation, etymology, or raw response.

## License

The maintainer releases his own contribution to this dataset under the **MIT License**.

The list was assembled from other sources, some under their own terms. This
dataset does not relicense them. The sources that `attested_by` names, with their
notices and licenses, are in
[`NOTICES.md`](https://huggingface.co/datasets/ryanjosephkamp/english-openlist/blob/main/NOTICES.md):
Wiktionary (CC BY-SA 4.0 and GFDL), WordNet 3.0 (Princeton's license), SCOWL and
the LibreOffice dictionaries (SCOWL's notice; the en_GB dictionary is LGPL),
ENABLE (public domain), and wordfreq (CC BY-SA 4.0 for its data). If you hold
rights in something here and want it removed or corrected, write to
ryanjosephkamp@gmail.com.

## Contact

- **Issues:** [GitHub Issues](https://github.com/ryanjosephkamp/english-openlist/issues)
- **Requests to correct or remove an entry:** ryanjosephkamp@gmail.com
- **Updates:** Check the `releases/` folder for version history
