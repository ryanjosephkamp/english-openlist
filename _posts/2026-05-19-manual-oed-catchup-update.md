---
title: "Manual OED Catch-Up Update — May 19, 2026"
date: 2026-05-19
tags: [update, manual, oed, dictionary]
---

# Manual OED Catch-Up Update — May 19, 2026

**Update Type:** Manual catch-up  
**Words added:** 201 new validated English unigrams  
**Source:** Oxford English Dictionary monthly update posts

## What Happened
During the period when the daily GitHub Action was inactive, several months of new-word additions from the Oxford English Dictionary were missed. This one-time manual catch-up was performed to bring the English OpenList fully up to date.

## Detailed Process
1. **Candidate Acquisition** — All new-word candidates were extracted from approximately 40 recent OED monthly update articles. Two distinct parsing methods were used: one for articles containing hyperlinked new words and another for articles using plain-text bullet lists.

2. **Rule Validation** — Every extracted candidate was passed through the strict English OpenList inclusion rules: unigrams only (no spaces or hyphens), letters a–z only, and length between 2 and 45 characters.

3. **Deduplication** — The full set of rule-passing candidates was deduplicated to remove any repeated entries across the different OED posts.

4. **Novelty Check** — The deduplicated list was compared against the current `merged_valid_words.txt` to remove any words already present in the English OpenList.

5. **Merriam-Webster Validation** — The remaining novel candidates were validated using the Merriam-Webster API (with Free Dictionary fallback). Only candidates that returned a clear `VALID` status were retained.

All 201 words that passed every stage have now been permanently added to the English OpenList.

## MW-Rejected OED Candidates
1,064 candidates from the OED updates did **not** validate as standard English words under Merriam-Webster (they were either not found, abbreviations, proper nouns, or otherwise excluded). The full list is preserved in `manual_catchup_2026-05/oed_mw_rejected.txt` for manual review.

## Interactive Statistics

### Starting Letter Distribution (full valid list)
<div class="manual-catchup-chart-container" style="position: relative; width: 100%; max-width: 900px; height: 420px; margin: 1.5rem auto;">
  <canvas id="startingLetterChart"></canvas>
</div>

### Word Length Distribution (full valid list)
<div class="manual-catchup-chart-container" style="position: relative; width: 100%; max-width: 900px; height: 420px; margin: 1.5rem auto;">
  <canvas id="wordLengthChart"></canvas>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="{{ '/assets/js/manual-catchup-charts.js' | relative_url }}"></script>

## Release Files
- `promoted_words.txt` — the 201 newly added words  
- `CHANGELOG.md` — detailed process log  
- `update_stats.json` — machine-readable summary  
- `starting_letter_distribution.csv` & `word_length_distribution.csv` — full-list versions used for the charts above

---

**This was a one-time manual update.** The daily automated GitHub Action is now back on its normal schedule and will continue adding new words each day.

---
