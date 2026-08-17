# SR2 — the all-zero stratum after full ingest

Measured 2026-08-17 over the assembled evidence matrix: **9,787,841 frame words**, 677 distinct binary evidence patterns.

## Reading A — binary detector patterns (S1–S3 posteriors)

| Pattern | Words | Share |
|---|---:|---:|
| `all-zero` | 8,858,214 | 90.50% |
| `wiktionary_english` | 414,125 | 4.23% |
| `wiktionary_english+web2+scowl` | 63,810 | 0.65% |
| `web2+scowl` | 38,058 | 0.39% |
| `wordnet+wiktionary_english+web2+hunspell_en_US+hunspell_en_GB+hunspell_en_CA+hunspell_en_AU+enable1+sowpods_legacy+nwl2023+csw21+scowl` | 33,049 | 0.34% |
| `scowl` | 32,264 | 0.33% |
| `wiktionary_english+sowpods_legacy+csw21+scowl` | 31,016 | 0.32% |
| `wiktionary_english+enable1+sowpods_legacy+nwl2023+csw21+scowl` | 30,460 | 0.31% |
| `wiktionary_english+hunspell_en_US+hunspell_en_GB+hunspell_en_CA+hunspell_en_AU+enable1+sowpods_legacy+nwl2023+csw21+scowl` | 27,915 | 0.29% |
| `hunspell_en_GB` | 23,347 | 0.24% |
| `wiktionary_english+scowl` | 19,016 | 0.19% |
| `wiktionary_english+hunspell_en_GB+enable1+sowpods_legacy+nwl2023+csw21+scowl` | 18,661 | 0.19% |

Biggest cell: `all-zero` at **90.50%** against the 50% threshold — SR2 under this reading **FIRES**.

## Reading B — undifferentiated after the corpus arm (S4/S5)

| Stratum | Words | Share |
|---|---:|---:|
| all-zero on every detector | 8,858,214 | 90.50% |
| …of which Google Books has data | 8,011,835 | 81.85% |
| …of which wordfreq has data | 123,906 | 1.27% |
| **no evidence of any kind** | **845,150** | **8.63%** |

Undifferentiated share: **8.63%** against the 50% threshold — SR2 under this reading **passes**.

## The verdict belongs to the protocol's owner

Reading A is the rule as written; reading B is the rule as motivated ("the majority of the population shares one posterior"). Under S1–S3 the binary pattern IS the posterior's whole input, so reading A is the honest bound for those specifications; under S4/S5 the corpus features differentiate within a pattern, and reading B measures what even they cannot reach. Neither reading is argued away here — the phase halts at this report either way, and which reading governs is recorded as a decision before Phase 2 proceeds.
