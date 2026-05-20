---
title: "Manual OED Catch-Up Update — May 19, 2026"
date: 2026-05-19
tags: [update, manual, oed, dictionary, interactive]
---

# Manual OED Catch-Up Update — May 19, 2026

**Update Type:** Manual catch-up  
**Words added:** 201 new validated English unigrams  

## Process Summary
We extracted candidates from ~40 OED monthly updates, applied strict unigram rules, deduplicated, checked novelty, and validated with Merriam-Webster.

## MW-Rejected Candidates
1,064 OED candidates did not validate under Merriam-Webster. Full list in `manual_catchup_2026-05/oed_mw_rejected.txt`.

## Interactive Statistics

### Starting Letter Distribution (full valid list)
<canvas id="startingLetterChart" width="800" height="400" style="background:#f8fafc;border:1px solid #e2e8f0"></canvas>

### Word Length Distribution (full valid list)
<canvas id="wordLengthChart" width="800" height="400" style="background:#f8fafc;border:1px solid #e2e8f0"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
console.log('🚀 Chart script started');

window.addEventListener('DOMContentLoaded', function() {
  console.log('✅ DOM ready – rendering charts');

  // Starting Letter Chart (test data)
  new Chart(document.getElementById('startingLetterChart'), {
    type: 'bar',
    data: {
      labels: ['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z'],
      datasets: [{
        label: 'Word Count',
        data: [19510,18363,31791,23363,15294,13021,11443,18577,13142,2120,3578,9967,27177,20300,13499,35709,3218,17659,34719,19654,12267,5326,5669,774,899,1641],
        backgroundColor: 'rgba(59, 130, 246, 0.85)'
      }]
    },
    options: { responsive: true, plugins: { legend: { display: false } } }
  });

  // Word Length Chart (test data)
  new Chart(document.getElementById('wordLengthChart'), {
    type: 'bar',
    data: {
      labels: Array.from({length: 20}, (_, i) => (i+1).toString()),
      datasets: [{
        label: 'Word Count',
        data: [10,134,1103,4265,9762,18110,29967,41770,47774,46229,41457,35463,28704,22453,17158,11403,7729,5188,3537,2245],
        backgroundColor: 'rgba(16, 185, 129, 0.85)'
      }]
    },
    options: { responsive: true, plugins: { legend: { display: false } } }
  });

  console.log('🎉 Charts rendered successfully!');
});
</script>

## Release Files
- `promoted_words.txt` — the 201 new words  
- `CHANGELOG.md` — full process log  
- `update_stats.json`  
- `starting_letter_distribution.csv` & `word_length_distribution.csv`

---

**This was a one-time manual update.** The daily GitHub Action is now back on schedule.
