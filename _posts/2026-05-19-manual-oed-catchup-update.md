---
title: "Manual OED Catch-Up Update — May 19, 2026"
date: 2026-05-19
tags: [update, manual, oed, dictionary, interactive]
---

# Manual OED Catch-Up Update — May 19, 2026

**Update Type:** Manual catch-up  
**Words added:** 201 new validated English unigrams  
**Source:** Oxford English Dictionary monthly update posts

## What Happened
During the recent period when the daily GitHub Action was inactive, we missed several months of new-word additions from the Oxford English Dictionary. This one-time manual catch-up brings the English OpenList fully up to date.

## Process Followed
1. Extracted all new-word candidates from ≈40 recent OED monthly update articles.  
2. Applied strict English OpenList inclusion rules (unigrams only, a-z letters only, length 2–45 characters, no spaces/hyphens).  
3. Deduplicated the full set.  
4. Performed novelty check against the current valid list.  
5. Ran full Merriam-Webster API validation (with Free Dictionary fallback).  

Only words that returned a clear **VALID** status were added.

## Newly Added Words
The complete list of 201 words is available in the [release folder on Hugging Face](https://huggingface.co/datasets/ryanjosephkamp/english-openlist/tree/main/releases/2026-05-19-manual-oed-catchup).

## MW-Rejected OED Candidates
1,064 candidates from the OED updates did **not** validate under Merriam-Webster. The full list is preserved in `manual_catchup_2026-05/oed_mw_rejected.txt`.

## Interactive Statistics

### Starting Letter Distribution (full valid list)
<canvas id="startingLetterChart" width="800" height="400"></canvas>

### Word Length Distribution (full valid list)
<canvas id="wordLengthChart" width="800" height="400"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
// Helper to parse CSV
async function loadCSV(url) {
  const response = await fetch(url);
  const text = await response.text();
  const rows = text.trim().split('\n').slice(1); // skip header
  return rows.map(row => {
    const [key, value] = row.split(',');
    return { key: key.trim(), value: parseInt(value.trim()) };
  });
}

// Load and render charts
async function renderCharts() {
  const base = "https://raw.githubusercontent.com/ryanjosephkamp/english-openlist/main/releases/2026-05-19-manual-oed-catchup/";

  // Starting Letter Chart
  const letterData = await loadCSV(base + "starting_letter_distribution.csv");
  const startingCtx = document.getElementById('startingLetterChart');
  new Chart(startingCtx, {
    type: 'bar',
    data: {
      labels: letterData.map(d => d.key.toUpperCase()),
      datasets: [{
        label: 'Word Count',
        data: letterData.map(d => d.value),
        backgroundColor: 'rgba(59, 130, 246, 0.85)',
        borderColor: 'rgba(59, 130, 246, 1)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { mode: 'index' } },
      scales: { y: { beginAtZero: true, title: { display: true, text: 'Number of Words' } } }
    }
  });

  // Word Length Chart
  const lengthData = await loadCSV(base + "word_length_distribution.csv");
  const lengthCtx = document.getElementById('wordLengthChart');
  new Chart(lengthCtx, {
    type: 'bar',
    data: {
      labels: lengthData.map(d => d.key),
      datasets: [{
        label: 'Word Count',
        data: lengthData.map(d => d.value),
        backgroundColor: 'rgba(16, 185, 129, 0.85)',
        borderColor: 'rgba(16, 185, 129, 1)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { mode: 'index' } },
      scales: {
        x: { title: { display: true, text: 'Word Length (characters)' } },
        y: { beginAtZero: true, title: { display: true, text: 'Number of Words' } }
      }
    }
  });
}

// Run when page loads
window.addEventListener('load', renderCharts);
</script>

## Release Files
- `promoted_words.txt` — the 201 new words  
- `CHANGELOG.md` — full process log  
- `update_stats.json`  
- `starting_letter_distribution.csv` & `word_length_distribution.csv` (full-list versions used above)

---

**This was a one-time manual update.** The daily GitHub Action is now back on its normal schedule.

---