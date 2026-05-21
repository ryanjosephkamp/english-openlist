---
title: "Manual OED Catch-Up Update — May 19, 2026"
date: 2026-05-19
tags: [update, manual, oed, dictionary, interactive]
---

# Manual OED Catch-Up Update — May 19, 2026

**Update Type:** Manual catch-up  
**Words added:** 201 new validated English unigrams  
**Source:** Oxford English Dictionary monthly update posts

## Process Followed
1. Extracted candidates from ~40 OED monthly updates.  
2. Applied strict unigram rules.  
3. Deduplicated.  
4. Checked novelty.  
5. Validated with Merriam-Webster API.

## MW-Rejected Candidates
1,064 OED candidates did **not** validate under Merriam-Webster. Full list preserved in `manual_catchup_2026-05/oed_mw_rejected.txt`.

## Interactive Statistics

### Starting Letter Distribution (full valid list)
<canvas id="startingLetterChart" width="800" height="400" style="background:#f8fafc;border:1px solid #e2e8f0"></canvas>

### Word Length Distribution (full valid list)
<canvas id="wordLengthChart" width="800" height="400" style="background:#f8fafc;border:1px solid #e2e8f0"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="/assets/js/manual-catchup-charts.js"></script>

## Release Files
- `promoted_words.txt` — the 201 new words  
- `CHANGELOG.md` — full process log  
- `update_stats.json`  
- `starting_letter_distribution.csv` & `word_length_distribution.csv`

---

**This was a one-time manual update.** The daily GitHub Action is now back on schedule.
