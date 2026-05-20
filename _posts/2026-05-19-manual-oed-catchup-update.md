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
<canvas id="startingLetterChart" width="800" height="400" style="background:#f8fafc; border:1px solid #e2e8f0;"></canvas>

### Word Length Distribution (full valid list)
<canvas id="wordLengthChart" width="800" height="400" style="background:#f8fafc; border:1px solid #e2e8f0;"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
console.log('🚀 Chart.js script started');

window.addEventListener('DOMContentLoaded', () => {
  console.log('✅ DOM fully loaded');

  const startingCtx = document.getElementById('startingLetterChart');
  const lengthCtx = document.getElementById('wordLengthChart');

  if (!startingCtx || !lengthCtx) {
    console.error('❌ Canvas elements not found!');
    return;
  }

  console.log('✅ Canvases found – rendering charts...');

  // Starting Letter Chart
  new Chart(startingCtx, {
    type: 'bar',
    data: {
      labels: ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z'],
      datasets: [{
        label: 'Word Count',
        data: [19510,18363,31791,23363,15294,13021,11443,18577,13142,2120,3578,9967,27177,20300,13499,35709,3218,17659,34719,19654,12267,5326,5669,774,899,1641],
        backgroundColor: 'rgba(59, 130, 246, 0.85)',
        borderColor: 'rgba(59, 130, 246, 1)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } }
    }
  });

  // Word Length Chart
  new Chart(lengthCtx, {
    type: 'bar',
    data: {
      labels: Array.from({length: 47}, (_, i) => (i+1).toString()),
      datasets: [{
        label: 'Word Count',
        data: [10,134,1103,4265,9762,18110,29967,41770,47774,46229,41457,35463,28704,22453,17158,11403,7729,5188,3537,2245,1429,886,617,403,276,185,110,83,64,49,31,21,16,12,11,7,5,1,2,3,1,1,0,0,0,0,3,2,1],
        backgroundColor: 'rgba(16, 185, 129, 0.85)',
        borderColor: 'rgba(16, 185, 129, 1)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { title: { display: true, text: 'Word Length (characters)' } },
        y: { beginAtZero: true }
      }
    }
  });

  console.log('🎉 Both charts rendered successfully!');
});
</script>

## Release Files
- `promoted_words.txt` — the 201 new words  
- `CHANGELOG.md` — full process log  
- `update_stats.json`  
- `starting_letter_distribution.csv` & `word_length_distribution.csv`

---

**This was a one-time manual update.** The daily GitHub Action is now back on its normal schedule.

---
