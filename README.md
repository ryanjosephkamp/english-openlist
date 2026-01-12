# Phase 3: Updating Pipeline

## Overview

Phase 3 transforms the English OpenList from a static dataset into a **living, continuously updated lexical resource**. This phase implements:

- 🔄 **Weekly automated dictionary scraping** via GitHub Actions
- 📦 **Public distribution** on Hugging Face Datasets
- 📊 **Statistical reports and visualizations** for each update
- 📝 **Version-controlled releases** with changelogs

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
export HF_TOKEN="your-huggingface-token"
```

Get your API keys:
- **Merriam-Webster:** [dictionaryapi.com](https://www.dictionaryapi.com/) (Free tier: 1000 requests/day)
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
│   ├── run_weekly_update.py    # Main orchestration script
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

The workflow at `.github/workflows/weekly_update.yml` runs every Sunday at 00:00 UTC.

### Required Secrets

Set these in your GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `MW_API_KEY` | Merriam-Webster API key |
| `HF_TOKEN` | Hugging Face write token |

### Manual Trigger

You can trigger the workflow manually from the GitHub Actions tab.

## Validation Rules

Words are valid if they:

✅ Contain only lowercase letters (a-z)  
✅ Are 2-45 characters in length  
✅ Are recognized by Merriam-Webster  
❌ Are NOT proper nouns  
❌ Are NOT abbreviations or acronyms  

## Output Files

Each weekly release generates:

| File | Description |
|------|-------------|
| `merged_valid_words.txt` | Updated valid word list |
| `merged_valid_dict.json` | Updated valid dictionary |
| `merged_invalid_words.txt` | Updated invalid list |
| `merged_invalid_dict.json` | Updated invalid dictionary |
| `CHANGELOG.md` | Summary of changes |
| `update_stats.json` | Machine-readable statistics |

## Testing

```bash
cd phase3
pytest tests/ -v
```

## Documentation

- [PHASE3_STRATEGY.md](PHASE3_STRATEGY.md) - Full strategy and architecture
- [templates/dataset_card.md](templates/dataset_card.md) - Hugging Face dataset description

## Status

| Component | Status |
|-----------|--------|
| Strategy Document | ✅ Complete |
| Configuration | ✅ Complete |
| Dictionary API | ✅ Complete |
| Word Validator | ✅ Complete |
| Data Updater | ✅ Complete |
| Main Pipeline | ✅ Complete |
| HF Uploader | ✅ Complete |
| GitHub Actions | ✅ Complete |
| Unit Tests | ✅ Complete |
| Integration Testing | ⏳ Pending |
| First Live Update | ⏳ Pending |

---

*Phase 3 - English OpenList Updating Pipeline*
