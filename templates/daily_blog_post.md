---
layout: post
title: "Daily English OpenList Update - {{ date }}"
date: {{ full_timestamp }}
categories: [daily-updates]
tags: [daily, statistics, words]
excerpt: "Automated English OpenList daily update for {{ date }}."
---

# Daily English OpenList Update — {{ date }}

**Generated automatically at {{ timestamp }} UTC**

This automated post reports recorded values only. Missing historical metrics are marked as `not recorded` or `unavailable` rather than reconstructed.

## Today's Results

- **Total words added today:** {{ words_added_today }}
- **New words discovered today:** {{ new_words_total }}
- **Words promoted from invalid list:** {{ promoted_count }}
- **Total valid words now:** **{{ total_valid_words }}**
- **Total invalid entries tracked:** {{ total_invalid_entries }}

{% if new_words %}
### New Words Discovered Today

```text
{{ new_words }}
```
{% endif %}

{% if promoted_words %}
### Words Promoted Today

```text
{{ promoted_words }}
```
{% endif %}

{% if chart_data %}
## Interactive Statistics

### Starting Letter Distribution

<div class="daily-update-chart-container">
  <canvas id="dailyStartingLetterChart" aria-label="Starting letter distribution chart" role="img"></canvas>
  <p class="daily-update-chart-fallback">Chart data is available as structured JSON in this post.</p>
</div>

### Word Length Distribution

<div class="daily-update-chart-container">
  <canvas id="dailyWordLengthChart" aria-label="Word length distribution chart" role="img"></canvas>
  <p class="daily-update-chart-fallback">Chart data is available as structured JSON in this post.</p>
</div>

<script id="daily-chart-data" type="application/json">{{ chart_data }}</script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="{{ '/assets/js/daily-update-charts.js' | relative_url }}"></script>
{% else %}
## Statistics Charts

Chart data was unavailable for this automated run, so no charts are shown for this post.
{% endif %}

## Execution Transparency

**API Health Check**
- Merriam-Webster API calls: {{ api_calls_mw }} ({{ api_success_mw }} success rate)
- Wordnik API calls: {{ api_calls_wordnik }} ({{ api_success_wordnik }} success rate)

**Words Discovered by Source**
- Merriam-Webster RSS / New Words: {{ from_rss }}
- Wordnik Word of the Day: {{ from_wordnik }}
- Invalid list validation: {{ from_invalid }}
- Manual additions: {{ from_manual }}

Missing historical metrics are shown as `not recorded` rather than reconstructed.

## Release Files

{{ release_files }}

*Generated automatically by the English OpenList daily pipeline.*
