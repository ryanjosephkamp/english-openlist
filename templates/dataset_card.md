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
---

# English OpenList

**The largest open-source, validated English word list for NLP and games.**

## Dataset Description

English OpenList is a comprehensive, continuously updated dictionary of valid English words. It provides:

- **378,666+ validated English words** following Scrabble-compatible rules
- **Rich metadata** including part of speech, definitions, and pronunciation
- **Weekly updates** from authoritative dictionary sources
- **Version history** with changelogs for every update

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
├── merged_valid_words.txt      # FULL valid word list (378,666+ words, one per line)
├── merged_valid_dict.json      # FULL dictionary with metadata for all valid words
├── merged_invalid_words.txt    # FULL invalid/rejected entries list
└── merged_invalid_dict.json    # FULL invalid dictionary with rejection reasons
```

### Daily Releases (releases/)

Daily updates with changelog and statistics:

```
releases/
└── {YYYY-MM-DD}/
    ├── promoted_words.txt      # Words promoted from invalid to valid that day
    ├── update_stats.json       # Statistics for the update
    └── CHANGELOG.md            # Changelog for the update
```

### Latest Update Reference (latest/)

Copy of the most recent release for convenience:

```
latest/
├── promoted_words.txt
├── update_stats.json
└── CHANGELOG.md
```

### Data Fields

**Valid Dictionary Entry:**
```json
{
  "word": "example",
  "source": "merriam-webster",
  "part_of_speech": "noun",
  "definition": "one that serves as a pattern...",
  "pronunciation": "ig-ˈzam-pəl",
  "validation_status": "valid",
  "added_date": "2026-01-12T00:00:00"
}
```

### Validation Rules (Scrabble-Compatible)

Words are included if they:
- ✅ Contain only lowercase letters (a-z)
- ✅ Are recognized by Merriam-Webster Collegiate Dictionary
- ✅ Are 2-45 characters in length
- ❌ Are NOT proper nouns (unless commonly used as verbs)
- ❌ Are NOT abbreviations or acronyms

## Dataset Statistics

| Metric | Value |
|--------|-------|
| Total Valid Words | 378,666+ |
| Total Invalid Entries | 9,275,000+ |
| Update Frequency | Daily (00:00 UTC) |
| Primary Source | Merriam-Webster Collegiate Dictionary |

## Usage

### Python (Hugging Face Datasets)

```python
from datasets import load_dataset

# Load the valid word list
dataset = load_dataset("english-openlist/english-openlist", split="train")

# Access words
for entry in dataset:
    print(entry["word"])
```

### Direct Download

**Download the complete word lists:**

```bash
# Download FULL valid words list (378,666+ words)
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

# Load dictionary for metadata
with open("merged_valid_dict.json", "r") as f:
    dictionary = json.load(f)

print(dictionary["example"]["definition"])
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
