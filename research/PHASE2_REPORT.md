# Phase 2 gate — held-out perplexity and negative-control separation

Measured 2026-08-17.

## Held-out perplexity

Per-character perplexity on the 20,219-word test partition: **7.034** (alphabet 27; uniform = 27; train-slice 6.542). Interpolation weights (uniform → order-4): [0.0009, 0.0033, 0.0248, 0.1269, 0.8442].

## Separation — AUC (positive ranks above family), Hanley-McNeil 95% CI

| Family | n | Feature | AUC | 95% CI | kept n⁺/n⁻ |
|---|---:|---|---:|---|---|
| ocr | 2,000 | `orthotactic_logp_per_char` | **0.897** | [0.887, 0.907] | 2,000/2,000 |
| ocr | 2,000 | `ocr_neighbor_freq_ratio` | — | too few non-NaN values | |
| ocr | 2,000 | `gb_tokens_per_volume` | **0.864** | [0.851, 0.877] | 2,000/835 |
| ocr | 2,000 | `gb_span_fill` | **0.818** | [0.802, 0.833] | 2,000/835 |
| ocr | 2,000 | `gb_log10_volume` | **0.974** | [0.969, 0.979] | 2,000/835 |
| ocr | 2,000 | `zipf_resid` | **0.964** | [0.957, 0.970] | 2,000/835 |
| ocr | 2,000 | `morph_productivity_vn` | **0.464** | [0.337, 0.591] | 1,123/21 |
| pseudo | 2,000 | `orthotactic_logp_per_char` | **0.530** | [0.513, 0.548] | 2,000/2,000 |
| pseudo | 2,000 | `ocr_neighbor_freq_ratio` | — | too few non-NaN values | |
| pseudo | 2,000 | `gb_tokens_per_volume` | **0.804** | [0.784, 0.824] | 2,000/369 |
| pseudo | 2,000 | `gb_span_fill` | **0.759** | [0.736, 0.782] | 2,000/369 |
| pseudo | 2,000 | `gb_log10_volume` | **0.950** | [0.942, 0.958] | 2,000/369 |
| pseudo | 2,000 | `zipf_resid` | **0.943** | [0.934, 0.952] | 2,000/369 |
| pseudo | 2,000 | `morph_productivity_vn` | **0.436** | [0.374, 0.497] | 1,123/97 |
| foreign | 2,000 | `orthotactic_logp_per_char` | **0.896** | [0.886, 0.906] | 2,000/2,000 |
| foreign | 2,000 | `ocr_neighbor_freq_ratio` | — | too few non-NaN values | |
| foreign | 2,000 | `gb_tokens_per_volume` | **0.684** | [0.657, 0.712] | 2,000/337 |
| foreign | 2,000 | `gb_span_fill` | **0.835** | [0.816, 0.853] | 2,000/337 |
| foreign | 2,000 | `gb_log10_volume` | **0.964** | [0.957, 0.971] | 2,000/337 |
| foreign | 2,000 | `zipf_resid` | **0.947** | [0.938, 0.956] | 2,000/337 |
| foreign | 2,000 | `morph_productivity_vn` | **0.416** | [0.230, 0.602] | 1,123/10 |
| mw_refuted | 441 | `orthotactic_logp_per_char` | **0.521** | [0.491, 0.550] | 2,000/441 |
| mw_refuted | 441 | `ocr_neighbor_freq_ratio` | — | too few non-NaN values | |
| mw_refuted | 441 | `gb_tokens_per_volume` | **0.828** | [0.786, 0.869] | 2,000/51 |
| mw_refuted | 441 | `gb_span_fill` | **0.839** | [0.800, 0.878] | 2,000/51 |
| mw_refuted | 441 | `gb_log10_volume` | **0.955** | [0.942, 0.969] | 2,000/51 |
| mw_refuted | 441 | `zipf_resid` | **0.946** | [0.930, 0.961] | 2,000/51 |
| mw_refuted | 441 | `morph_productivity_vn` | **0.332** | [0.299, 0.365] | 1,123/386 |

## SR3 — can the corpus arm tell scan artifacts from rare real words?

OCR corruptions Google Books actually contains: **835** of 2,000. Rare real words (held-out positives, volume ≤ Q1 = 26976): **5,054**.

| Corpus feature | AUC (rare-real above artifact) | 95% CI |
|---|---:|---|
| `ocr_neighbor_freq_ratio` | **0.977** | [0.962, 0.991] — separates |
| `gb_tokens_per_volume` | **0.722** | [0.706, 0.738] — separates |
| `gb_span_fill` | **0.747** | [0.732, 0.763] — separates |
| `gb_log10_volume` | **0.899** | [0.891, 0.908] — separates |
| `zipf_resid` | **0.897** | [0.888, 0.905] — separates |

**SR3 passes**: `ocr_neighbor_freq_ratio`, `gb_tokens_per_volume`, `gb_span_fill`, `gb_log10_volume`, `zipf_resid` exclude 0.5.


## The typed-neighbour asymmetry (D-012)

Share of words with ANY typed OCR back-neighbour in the reference lexicon — the number Phase 0 could not get from raw edit distance, which fired on 50.5% of a real-word control:

| Set | Fires | Rate |
|---|---:|---:|
| held-out positives | 7/2,000 | 0.3% |
| ocr | 1,349/2,000 | 67.5% |
| pseudo | 6/2,000 | 0.3% |
| foreign | 3/2,000 | 0.1% |
| mw_refuted | 0/441 | 0.0% |

Family sizes: {'ocr': 2000, 'pseudo': 2000, 'foreign': 2000, 'mw_refuted': 441}. Positives: 2,000 of 20,219 held-out test words, sha256-selected.
