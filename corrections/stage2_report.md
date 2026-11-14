# Stage 2 — how often was the LLM wrong?

400 words sampled from the 20,052 carrying `"status": "invalid"`, stratified by how many corpora attested them. Every one of those verdicts came from a single pass by Google Gemini 3 Flash Preview in December 2025.

**No word was moved.** This stage measures.

A dictionary having the word means the LLM was wrong. A dictionary *not* having it means nothing either way — much of this vocabulary is technical, and absence from Merriam-Webster is not evidence of absence from English. So the figures below are a **lower bound** on the error rate.

## As measured

| Stratum | Population | Sampled | Refuted | Corroborated | Unadjudicated | Error | Error rate (95% CI) |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 448 | 40 | 3 | 0 | 37 | 0 | 100.0% (44–100%) |
| 1 | 10,056 | 160 | 1 | 0 | 159 | 0 | 100.0% (21–100%) |
| 2 | 4,906 | 80 | 1 | 1 | 78 | 0 | 50.0% (9–91%) |
| 3 | 2,254 | 60 | 4 | 0 | 56 | 0 | 100.0% (51–100%) |
| 4+ | 2,388 | 60 | 4 | 4 | 52 | 0 | 50.0% (22–78%) |

**Weighted error rate across all 20,052 words: 81.8% (95% CI 64.4% – 99.3%).**

Adjudicable: **18 of 400** sampled words (4.5%). The rest had no entry in any source consulted, which says nothing about whether they are words.

## Counting only Merriam-Webster rulings

Free Dictionary performs no abbreviation or proper-noun screening, so it returns `valid` for entries Merriam-Webster would reject. Recomputed with Free-Dictionary-only rulings demoted to unadjudicated:

| Stratum | Population | Sampled | Refuted | Corroborated | Unadjudicated | Error | Error rate (95% CI) |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 448 | 40 | 3 | 0 | 37 | 0 | 100.0% (44–100%) |
| 1 | 10,056 | 160 | 1 | 0 | 159 | 0 | 100.0% (21–100%) |
| 2 | 4,906 | 80 | 1 | 1 | 78 | 0 | 50.0% (9–91%) |
| 3 | 2,254 | 60 | 4 | 0 | 56 | 0 | 100.0% (51–100%) |
| 4+ | 2,388 | 60 | 3 | 4 | 53 | 0 | 42.9% (16–75%) |

**Weighted error rate across all 20,052 words: 81.0% (95% CI 63.5% – 98.5%).**

Adjudicable: **17 of 400** sampled words (4.2%). The rest had no entry in any source consulted, which says nothing about whether they are words.

## Which source ruled

| Source | Words ruled |
|---|---:|
| (none) | 382 |
| collegiate | 10 |
| medical | 7 |
| free | 1 |

**Lookups where at least one source errored rather than answering: 298.** An error is a statement about our quota or the network, never about the word, and is never recorded as "not found".

