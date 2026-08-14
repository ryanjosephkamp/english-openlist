# Stage 2 — how often was the LLM wrong?

6 words sampled from the 20,052 carrying `"status": "invalid"`, stratified by how many corpora attested them. Every one of those verdicts came from a single pass by Google Gemini 3 Flash Preview in December 2025.

**No word was moved.** This stage measures.

A dictionary having the word means the LLM was wrong. A dictionary *not* having it means nothing either way — much of this vocabulary is technical, and absence from Merriam-Webster is not evidence of absence from English. So the figures below are a **lower bound** on the error rate.

## As measured

| Stratum | Population | Sampled | Refuted | Corroborated | Unadjudicated | Error | Error rate (95% CI) |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 448 | 6 | 0 | 0 | 6 | 0 | nothing adjudicable |
| 1 | 10,056 | 0 | 0 | 0 | 0 | 0 | nothing adjudicable |
| 2 | 4,906 | 0 | 0 | 0 | 0 | 0 | nothing adjudicable |
| 3 | 2,254 | 0 | 0 | 0 | 0 | 0 | nothing adjudicable |
| 4+ | 2,388 | 0 | 0 | 0 | 0 | 0 | nothing adjudicable |

**Weighted error rate across all 20,052 words: n/a (95% CI n/a – n/a).**

Adjudicable: **0 of 6** sampled words (0.0%). The rest had no entry in any source consulted, which says nothing about whether they are words.

## Counting only Merriam-Webster rulings

Free Dictionary performs no abbreviation or proper-noun screening, so it returns `valid` for entries Merriam-Webster would reject. Recomputed with Free-Dictionary-only rulings demoted to unadjudicated:

| Stratum | Population | Sampled | Refuted | Corroborated | Unadjudicated | Error | Error rate (95% CI) |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 448 | 6 | 0 | 0 | 6 | 0 | nothing adjudicable |
| 1 | 10,056 | 0 | 0 | 0 | 0 | 0 | nothing adjudicable |
| 2 | 4,906 | 0 | 0 | 0 | 0 | 0 | nothing adjudicable |
| 3 | 2,254 | 0 | 0 | 0 | 0 | 0 | nothing adjudicable |
| 4+ | 2,388 | 0 | 0 | 0 | 0 | 0 | nothing adjudicable |

**Weighted error rate across all 20,052 words: n/a (95% CI n/a – n/a).**

Adjudicable: **0 of 6** sampled words (0.0%). The rest had no entry in any source consulted, which says nothing about whether they are words.

## Which source ruled

| Source | Words ruled |
|---|---:|
| (none) | 6 |

**Lookups where at least one source errored rather than answering: 4.** An error is a statement about our quota or the network, never about the word, and is never recorded as "not found".

