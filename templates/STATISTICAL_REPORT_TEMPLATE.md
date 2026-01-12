# English OpenList Statistical Report

## Update: {DATE}

---

## 1. Update Summary

| Metric | Value |
|--------|-------|
| Update Date | {DATE} |
| Words Added | {WORDS_ADDED} |
| Words Promoted | {WORDS_PROMOTED} |
| Total Valid Words | {TOTAL_VALID} |
| Total Invalid Words | {TOTAL_INVALID} |
| Processing Duration | {DURATION} |

---

## 2. Word List Growth

### 2.1 Valid Words Over Time

```
{GROWTH_CHART_ASCII}
```

### 2.2 Weekly Addition Rate

| Week | Date | Words Added | Cumulative Total |
|------|------|-------------|------------------|
{WEEKLY_ADDITIONS_TABLE}

---

## 3. Word Length Distribution

### 3.1 Valid Words by Length

| Length | Count | Percentage |
|--------|-------|------------|
{LENGTH_DISTRIBUTION_TABLE}

### 3.2 Distribution Visualization

![Word Length Distribution](figures/word_length_distribution.png)

---

## 4. Part of Speech Breakdown

| Part of Speech | Count | Percentage |
|----------------|-------|------------|
{POS_DISTRIBUTION_TABLE}

![Part of Speech Distribution](figures/part_of_speech_breakdown.png)

---

## 5. Letter Frequency Analysis

### 5.1 Starting Letters

| Letter | Count | Percentage |
|--------|-------|------------|
{STARTING_LETTER_TABLE}

### 5.2 Letter Frequency in Valid Words

![Letter Frequency](figures/letter_frequency.png)

---

## 6. Source Attribution

| Source | Words Contributed | Percentage |
|--------|-------------------|------------|
{SOURCE_ATTRIBUTION_TABLE}

---

## 7. Methodology

### 7.1 Data Sources

This update queried the following authoritative sources:
{SOURCES_LIST}

### 7.2 Validation Pipeline

1. **Discovery:** New word candidates identified from dictionary feeds
2. **Rule Validation:** Candidates checked against Scrabble-compatible rules
   - Lowercase alphabetic only (a-z)
   - Length: 2-45 characters
   - No proper nouns
3. **API Validation:** Candidates verified against Merriam-Webster API
4. **Update:** Valid words added to list, promoted from invalid if present

### 7.3 Quality Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| False Positive Rate | <2.5% | {FP_RATE} |
| API Error Rate | <1% | {API_ERROR_RATE} |
| Processing Success | >99% | {SUCCESS_RATE} |

---

## 8. Files Generated

| File | Description | Size |
|------|-------------|------|
{FILES_TABLE}

---

*Report generated: {TIMESTAMP}*
*English OpenList Phase 3 - Automated Statistical Report*
