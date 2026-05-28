# Phase 3: Updating Pipeline

## Overview

Phase 3 transforms the English OpenList from a static dataset into a **living, continuously updated lexical resource**. This phase implements:

- 🔄 **Daily automated word discovery** via GitHub Actions
- 🔍 **Multi-source discovery** from Merriam-Webster RSS, MW New Words page, and Wordnik API
- 🔎 **Invalid list recovery** - validates ~1,000 words/day from the invalid list
- 📦 **Public distribution** on Hugging Face Datasets
- 📊 **Statistical reports and visualizations** for each update
- 📝 **Version-controlled releases** with consolidated changelogs

## Quick Start

### 1. Install Dependencies

```bash
cd phase3
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file or set environment variables:

```bash
export MW_API_KEY="your-merriam-webster-api-key"
export MW_MEDICAL_API_KEY="your-merriam-webster-medical-api-key"  # Optional
export WORDNIK_API_KEY="your-wordnik-api-key"  # Optional, for Word of the Day
export HF_TOKEN="your-huggingface-token"
```

Get your API keys:
- **Merriam-Webster:** [dictionaryapi.com](https://www.dictionaryapi.com/) (Free tier: 1000 requests/day)
- **Wordnik:** [developer.wordnik.com](https://developer.wordnik.com/) (Free tier: 100 requests/day)
- **Hugging Face:** [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)

### 3. Run Manual Update

```bash
python scripts/run_weekly_update.py
```

### 4. Upload to Hugging Face

```bash
python scripts/push_to_huggingface.py
```

## Project Structure

```
phase3/
├── PHASE3_STRATEGY.md          # Comprehensive strategy document
├── README.md                   # This file
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── initial_deliverables/       # Input data from Phases 1-2
│   ├── merged_valid_words.txt
│   ├── merged_valid_dict.json
│   ├── merged_invalid_words.txt
│   └── merged_invalid_dict.json
├── scripts/
│   ├── dictionary_api.py       # Merriam-Webster API wrapper
│   ├── word_validator.py       # Scrabble-compatible validation
│   ├── data_updater.py         # List/dictionary update logic
│   ├── run_weekly_update.py    # Main orchestration (new word discovery)
│   ├── validate_invalid_list.py # Invalid list recovery pipeline
│   ├── generate_changelog.py   # Consolidated changelog generator
│   ├── download_from_huggingface.py # Download data from HF
│   └── push_to_huggingface.py  # Hugging Face upload
├── templates/
│   ├── dataset_card.md         # Hugging Face README template
│   ├── CHANGELOG_TEMPLATE.md   # Changelog format
│   └── STATISTICAL_REPORT_TEMPLATE.md
├── tests/
│   └── test_word_validator.py  # Unit tests
├── output/                     # Generated release files
└── logs/                       # Pipeline logs
```

## GitHub Actions Automation

The workflow at `.github/workflows/daily_update.yml` runs **daily at 00:00 UTC**.

### Daily Pipeline

1. **New Word Discovery** - Discovers words from multiple sources:
   - Merriam-Webster RSS feed (Word of the Day)
   - Merriam-Webster "New Words in the Dictionary" page
   - Wordnik Word of the Day (past 30 days)
   - Manual additions file (`manual_additions.txt`)

2. **Invalid List Validation** - Validates ~1,000 words/day from the invalid list against MW API, promoting valid words

3. **Changelog Generation** - Creates consolidated changelog with all changes

4. **Hugging Face Upload** - Pushes updated word lists to HF Datasets

### Required Secrets

Set these in your GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `MW_API_KEY` | Merriam-Webster Collegiate API key |
| `MW_MEDICAL_API_KEY` | Merriam-Webster Medical API key (optional) |
| `WORDNIK_API_KEY` | Wordnik API key (optional, for WOTD discovery) |
| `HF_TOKEN` | Hugging Face write token |

### Manual Trigger

You can trigger the workflow manually from the GitHub Actions tab with optional parameters:
- `validation_limit` - Number of invalid words to validate (default: 1000)
- `skip_upload` - Skip uploading to Hugging Face
- `skip_invalid_validation` - Skip invalid list validation

## Validation Rules

Words are valid if they:

✅ Contain only lowercase letters (a-z)  
✅ Are 2-45 characters in length  
✅ Are recognized by Merriam-Webster  
❌ Are NOT proper nouns  
❌ Are NOT abbreviations or acronyms  

## Output Files

Each daily release generates (in `output/YYYY-MM-DD/`):

| File | Description |
|------|-------------|
| `merged_valid_words.txt` | Updated valid word list |
| `merged_valid_dict.json` | Updated valid dictionary |
| `merged_invalid_words.txt` | Updated invalid list |
| `merged_invalid_dict.json` | Updated invalid dictionary |
| `promoted_words.txt` | Words promoted from invalid → valid today |
| `CHANGELOG.md` | Consolidated summary of all changes |
| `update_stats.json` | Machine-readable statistics |

Daily automation also generates transient Brrrdle artifacts in `output/YYYY-MM-DD/brrrdle/`.
These files are uploaded to Hugging Face under both `latest/brrrdle/` and `data/brrrdle/`,
but are not committed as repository data folders.

### Brrrdle Artifacts

`words_length_{N}.json` files are the primary Brrrdle artifacts, with one file for
each word length from 2 through 35. Each file contains `metadata.curation`,
curated `answers`, and complete `validGuesses`. The `validGuesses` array remains
the full per-length list, while `answers` is generated with the deterministic
`stratified_quality_score_v1` method using seed `42 + length`. Both arrays contain
plain word strings.

For one transition period, the generator also publishes the legacy length-5
compatibility files `brrrdle_words.txt` and `brrrdle_words.json`. In the next
major Brrrdle artifact update, remove those legacy files and any legacy-only
manifest or generated README behavior that remains.

## Testing

```bash
cd phase3
pytest tests/ -v
```

## Documentation

- [PHASE3_STRATEGY.md](PHASE3_STRATEGY.md) - Full strategy and architecture
- [templates/dataset_card.md](templates/dataset_card.md) - Hugging Face dataset description

## Word Discovery Sources

The pipeline automatically discovers new words from multiple sources:

| Source | Description | Frequency |
|--------|-------------|----------|
| MW RSS Feed | Merriam-Webster Word of the Day | Daily |
| MW New Words Page | Newly added dictionary entries | Daily |
| Wordnik WOTD | Wordnik Word of the Day (past 30 days) | Daily |
| Manual Additions | `manual_additions.txt` file | On commit |
| Invalid List Recovery | Validates candidates from invalid list | ~1,000/day |

## Status

| Component | Status |
|-----------|--------|
| Strategy Document | ✅ Complete |
| Configuration | ✅ Complete |
| Dictionary API | ✅ Complete |
| Word Validator | ✅ Complete |
| Data Updater | ✅ Complete |
| Main Pipeline | ✅ Complete |
| Multi-Source Discovery | ✅ Complete |
| Invalid List Validator | ✅ Complete |
| Abbreviation Filtering | ✅ Complete |
| Consolidated Changelog | ✅ Complete |
| HF Uploader | ✅ Complete |
| GitHub Actions | ✅ Complete |
| Unit Tests | ✅ Complete |
| Integration Testing | ✅ Complete |
| First Live Update | ✅ Complete (94+ successful daily runs; workflow re-enabled after inactivity) |

---

*Phase 3 - English OpenList Updating Pipeline*
