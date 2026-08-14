---
annotations_creators:
  - machine-generated
  - expert-generated
language:
  - en
language_creators:
  - found
license: mit
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
  - scrabble
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

**The largest open-source, validated English word list for NLP and games.**

## Dataset Description

English OpenList is a comprehensive, continuously updated dictionary of valid English words. It provides:

- **~379,000 validated English words** following Scrabble-compatible rules
- **Validation provenance** for every word: which sources attested it, and when
- **Daily updates** from authoritative dictionary sources
- **Version history** with changelogs for every update

> **What the metadata is.** `merged_valid_dict.json` records *how each word was
> validated* — the sources that attested it, the checks it passed, and the dates.
> It does **not** contain definitions, parts of speech, pronunciations, or
> frequency data. If you need those, pair this list with WordNet or Wiktionary.

### Why Use English OpenList?

| Use Case | Benefit |
|----------|---------|
| **Spell Checking** | High-precision word validation |
| **Word Games** | Scrabble/Wordle compatible list |
| **NLP Training** | Clean, validated vocabulary |
| **Research** | Transparent methodology, full provenance |

## Dataset Structure

### Full Word Lists (data/)

**These are the complete, up-to-date word lists that most users will want to download:**

```
data/
├── merged_valid_words.txt      # FULL valid word list (~379,000 words, one per line)
├── merged_valid_dict.json      # FULL dictionary with metadata for all valid words
├── merged_invalid_words.txt    # FULL invalid/rejected entries list
└── merged_invalid_dict.json    # FULL invalid dictionary with rejection reasons
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

Entries are **not** uniformly shaped. The list was assembled from several
intakes, and each kept the fields its own pipeline produced. Read defensively:
check for a field before using it.

**Tournament word list intake** — the largest group:

```json
{
  "word": "broth",
  "source": "twl_scrabble_dictionary",
  "validation_status": "valid",
  "added_date": "2026-01-10",
  "length": 5
}
```

**Verification pipeline intake** — carries `candidate_source`, whose entries are
suffixed `_valid` or `_unlikely`. Count only the `_valid` ones; a word can carry
eight sources that all say *unlikely*:

```json
{
  "word": "a",
  "unverified_llm_verdict": "valid",
  "validation_source": "verification_pipeline",
  "candidate_source": ["google_ngrams_valid", "wordnet_valid", "nltk_valid"],
  "advanced_validation": { "passed": true, "confidence": 1.0 },
  "statistical_validation": { "passed": true, "perplexity": 1.0 },
  "proper_noun_check": { "checked": true, "is_proper_noun": false },
  "added_date": "2025-12-17"
}
```

> **`unverified_llm_verdict` was called `status` until 14 August 2026.** It was
> renamed because the old name made it read like this dataset's own ruling, and
> it is not one. It records what a single LLM pass (Google Gemini 3 Flash
> Preview, December 2025) thought of the word, on 137,705 entries. **Do not
> filter on it expecting a validation result.** Its accuracy was measured — see
> *Known limitations* below — and it was wrong more often than right wherever a
> real dictionary could check.
>
> A separate `dictionary_verdict` field appears on 201 entries. That one *is* a
> dictionary ruling, from Merriam-Webster or Free Dictionary via the promotion
> path, and its `source` field names which.

**Synthetic intake** — algorithmically constructed candidates, identifiable by
`source: "synthetic_generation"`:

```json
{
  "source": "synthetic_generation",
  "category": "Medical",
  "valid": 1,
  "validated": true,
  "notes": "Synthetic candidate awaiting validation",
  "created_date": "2026-01-11T12:19:00"
}
```

Note the synthetic records have no `word` field — the word is the object key.

### Validation Rules (Scrabble-Compatible)

These are the rules applied to **newly discovered words** by the daily pipeline:

- ✅ Contain only lowercase letters (a-z)
- ✅ Are recognized by Merriam-Webster Collegiate Dictionary
- ❌ Are NOT proper nouns (unless commonly used as verbs)
- ❌ Are NOT abbreviations or acronyms

Words already in the list arrived through earlier intakes and were not all
checked against Merriam-Webster — see *Composition* below. Lengths run from 1 to
47 characters (`a` at one end, `phosphoribosylaminoimidazolesuccinocarboxamides`
at the other).

## Dataset Statistics

| Metric | Value |
|--------|-------|
| Total Valid Words | ~345,000 (grows daily) |
| Total Invalid Entries | 9,275,000+ |
| Update Frequency | Daily (00:00 UTC) |
| Primary Source for New Words | Merriam-Webster Collegiate Dictionary |

Counts here are approximate by design — the list grows every day. For the exact
current figure see [`latest/update_stats.json`](https://huggingface.co/datasets/ryanjosephkamp/english-openlist/blob/main/latest/update_stats.json).

### Composition

The list was assembled from several intakes over time, and they are not
interchangeable. Anyone filtering or scoring this data should know the mix:

| Intake | Share | How to identify |
|--------|-------|-----------------|
| Tournament word list | ~46% | `source: "twl_scrabble_dictionary"` |
| Verification pipeline | ~35% | `validation_source: "verification_pipeline"` |
| Synthetic candidates | ~17% | `source: "synthetic_generation"` |
| Other / unattested | ~2% | none of the above |

The synthetic group contains algorithmically constructed forms such as
`abacteremicer` and `nonlivabler`. They are kept deliberately — this list aims
to be broad, and removing them would narrow it — but they are the group most
likely to surprise you, and applications wanting only conventional vocabulary
should filter on `source`.

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

# Load the dictionary for validation provenance.
# Note this file is ~290 MB; stream it if memory is tight.
with open("merged_valid_dict.json", "r") as f:
    dictionary = json.load(f)

entry = dictionary["broth"]
print(entry["source"])             # twl_scrabble_dictionary
print(entry.get("candidate_source"))  # None on this intake -- check before use
```

## Methodology

### Phase 1: Corpus Acquisition (December 2025)

Aggregated 9.8 million candidate words from 15+ open sources:
- Wiktionary (6.5M words)
- WordNet 3.1 (150K words)
- SCOWL 2020 (500K words)
- Google Books Ngrams (1M+ words)
- Collins Complete Dictionary (800K words)

### Phase 2: Validation Pipeline (December 2025 - January 2026)

Multi-stage AI validation using Gemini 2.0/2.5 Flash:
- Pattern-based screening
- LLM classification with iterative convergence
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

**13 August 2026.** 150 words were in `merged_valid_words.txt` and in
`merged_invalid_words.txt` at the same time — words the daily pipeline had
promoted onto one side without removing them from the other. Every one already
carried a dictionary API ruling in its own record (Merriam-Webster for 63, Free
Dictionary for 86, MW Medical for 1), so all 150 were cleared as valid and
removed from the invalid list. **None was demoted, and the valid word list did
not change.** 201 entries whose `status` field (now `dictionary_verdict`) read `"WordStatus.VALID"` — a
stringified Python enum — were normalised to `"valid"` in the same change.

**14 August 2026 — the `status` field was renamed, and measured.**

`status` read like this dataset's verdict on a word. It was not: on 137,705
entries it recorded what one LLM pass (Google Gemini 3 Flash Preview, December
2025) thought. It is now `unverified_llm_verdict`, so nobody has to read the
documentation to find that out.

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
is kept with its provenance and clearly labelled, rather than acted on or
quietly deleted.

**14 August 2026 — 33,594 synthetic forms were demoted.**

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
invalid.** A demotion here means no dictionary we could reach recognised the
word on that date — not that it is not a word. Every demoted word is in a
recheck queue that the daily pipeline draws from on a reserved part of each
night, bypassing the length filter that would otherwise hide the longer ones
indefinitely. Each one names its reason in
[`corrections/ledger_demotions.csv`](https://github.com/ryanjosephkamp/english-openlist/tree/main/corrections).

Two known issues remain, **deliberately not acted on**:

- **20,052 entries carry `unverified_llm_verdict: "invalid"` while listed as
  valid.** Treat it as one machine's opinion from December 2025, not a
  validation result. Where it could be checked it was wrong more often than
  right.
- **31,243 entries from the synthetic intake carry no attestation at all** — no
  corpus source and no validation record — while marked `validated: true`.

  **These were deliberately kept, not overlooked.** Most are plurals, and when
  Merriam-Webster was asked about those it could rule on only 9.2% of their
  stems — but accepted four of the eleven it could: `bioterrorisms`,
  `defamiliarizations`, `ebullisms`, `ferroelectricities`. Demoting a group on
  that evidence would have discarded real words. Settling them needs a source
  that covers technical nouns, which Merriam-Webster does not.

  If you need only words a human source attested, filter on
  `source != "synthetic_generation"`.

## Citation

```bibtex
@dataset{english_openlist_2026,
  title = {English OpenList: A Comprehensive Validated English Word List},
  author = {English OpenList Project Team},
  year = {2026},
  publisher = {Hugging Face},
  url = {https://huggingface.co/datasets/english-openlist/english-openlist}
}
```

## License

This dataset is released under the **MIT License**.

The underlying word data is derived from open sources with compatible licenses.

## Contact

- **Issues:** [GitHub Issues](https://github.com/english-openlist/english-openlist/issues)
- **Updates:** Check the `releases/` folder for version history

---

*Last Updated: January 2026*
