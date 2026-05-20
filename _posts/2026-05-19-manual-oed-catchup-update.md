---
title: "Manual OED Catch-Up Update — May 19, 2026"
date: 2026-05-19
tags: [update, manual, oed, dictionary, interactive]
---

# Manual OED Catch-Up Update — May 19, 2026

**Update Type:** Manual catch-up  
**Words added:** 201 new validated English unigrams  

## Process Summary
We extracted candidates from OED monthly updates, applied strict unigram rules, deduplicated, checked novelty, and validated with Merriam-Webster.

## MW-Rejected Candidates
1,064 OED candidates did **not** validate under Merriam-Webster. Full list in `manual_catchup_2026-05/oed_mw_rejected.txt`.

## Interactive Statistics

### Starting Letter Distribution (test version)
<canvas id="startingLetterChart" width="800" height="400" style="background:#f8fafc;border:1px solid #e2e8f0"></canvas>

### Word Length Distribution (test version)
<canvas id="wordLengthChart" width="800" height="400" style="background:#f8fafc;border:1px solid #e2e8f0"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
console.log('🚀 Chart script started');

window.addEventListener('DOMContentLoaded', function() {
  console.log('✅ DOM ready');

  // Starting Letter Chart (short test data)
  new Chart(document.getElementById('startingLetterChart'), {
    type: 'bar',
    data: {
      labels: ['A','B','C','D','E'],
      datasets: [{ label: 'Count', data: [100,80,120,90,110], backgroundColor: 'rgba(59, 130, 246, 0.85)' }]
    },
    options: { responsive: true, plugins: { legend: { display: false } } }
  });

  // Word Length Chart (short test data)
  new Chart(document.getElementById('wordLengthChart'), {
    type: 'bar',
    data: {
      labels: ['3','4','5','6','7'],
      datasets: [{ label: 'Count', data: [1000,2000,3000,2500,1800], backgroundColor: 'rgba(16, 185, 129, 0.85)' }]
    },
    options: { responsive: true, plugins: { legend: { display: false } } }
  });

  console.log('🎉 Charts should now be visible!');
});
</script>

## Release Files
- `promoted_words.txt` — the 201 new words  
- `CHANGELOG.md` — full process log  
- `update_stats.json`  
- `starting_letter_distribution.csv` & `word_length_distribution.csv`

---

**This was a one-time manual update.** The daily GitHub Action is now back on schedule.
