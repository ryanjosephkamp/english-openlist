# BRRRDLE-ANSWERS-CURATION-SPEC.md

**Project:** english-openlist  
**Date:** 2026-05-27  
**Status:** Binding specification for Copilot agent  
**Purpose:** Define the exact algorithm that must be used to generate the `answers` array in every `words_length_N.json` file for brrrdle.

This document is the single source of truth for the new `answers` curation logic.

### 1. Requirements (Locked-in)

For every word length `N` (2 through 35):

1. **`validGuesses`** must always be the **complete, unfiltered list** of all words of length `N` from the English OpenList (no changes to existing behavior).

2. **`answers`** must be a curated subset of `validGuesses` using the following rules:

   - **Rule 1** (small lists): If `len(validGuesses) < 1000`, then `answers = validGuesses` (full list, sorted alphabetically).

   - **Rule 2** (large lists): If `len(validGuesses) >= 1000`, use **stratified sampling by starting letter** + **quality-score ranking** inside each bucket.

### 2. Target Sample Size (Dynamic)

```python
import math

def get_target_sample_size(total_valid_guesses: int) -> int:
    if total_valid_guesses < 1000:
        return total_valid_guesses
    target = int(math.sqrt(total_valid_guesses) * 22)
    return max(2000, min(8000, target))
```

### 3. Deterministic Seed

`random.seed(42 + length)` for every length `N`.

### 4. Quality Score Formula (Approved)

For a word `w` inside its starting-letter bucket:

```python
quality_score(w) = 
    0.45 × letter_frequency_similarity(w) +
    0.30 × positional_match_score(w) +
    0.15 × vowel_consonant_balance_score(w) +
    0.10 × uniqueness_score(w)
```

All components normalized to [0, 1].

### 5. Full Ready-to-Use Python Function

The agent must add (or extend) the following function in the preprocessing pipeline:

```python
from collections import Counter, defaultdict
import random
import math
from datetime import datetime, timezone
from typing import List, Dict, Any

# ... (include the full create_word_list_json function from our previous conversation, including all helpers)

def create_word_list_json(valid_guesses: List[str], length: int) -> Dict[str, Any]:
    # Full implementation as previously provided
    ...
```

### 6. Metadata to Include in Every JSON

Each `words_length_N.json` must contain this metadata structure (merge with existing metadata):

```json
{
  "metadata": {
    "curation": {
      "method": "stratified_quality_score_v1",
      "seed": 54,
      "target_sample_size": 3800,
      "curation_date": "2026-05-27T18:00:00Z",
      "note": "Stratified by starting letter + quality score (frequency 0.45, positional 0.30, vowel balance 0.15, uniqueness 0.10)"
    }
  },
  "answers": [...],
  "validGuesses": [...]
}
```

### 7. Integration Instructions for the Agent

- The preprocessing logic lives primarily in `generate_brrrdle_artifacts.py` (and any supporting scripts).
- The agent must **add** the new curation function and call it when generating the brrrdle artifacts.
- **Do not delete** any existing logic — extend the current pipeline to also populate the `answers` key.
- Keep changes minimal: only modify files that are directly relevant to brrrdle JSON generation.
- Update the daily GitHub Action (`daily_update.yml`) only if needed to call the new logic.
- Create a new changelog entry in the appropriate change-logs folder.

The agent must **halt** after drafting the implementation plan and wait for explicit user approval before making any code changes.

---
