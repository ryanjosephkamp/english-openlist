# Stage 3 — are the synthetic comparatives real?

300 stems sampled from the 8,809 behind the 16,478 synthetic `-er`/`-est` forms in the valid list — words like `abacteremicer`, `abambulacralest` and `abatabler`.

**No word was moved.** This stage measures.

The question is not whether Merriam-Webster carries the comparative as a headword — it never would. It is whether MW lists the comparative among the inflections of its stem, in `meta.stems`. A "no" there is the dictionary enumerating a word's forms and leaving this one out.

## Coverage — can the question be answered at all?

| Stratum | Stems | Sampled | MW ruled | Coverage |
|---|---:|---:|---:|---:|
| WordNet adjective | 1,717 | 100 | 94 | 94.0% |
| WordNet noun/verb only | 306 | 50 | 46 | 92.0% |
| not in WordNet | 6,786 | 150 | 43 | 28.7% |
| **Total** | **8,809** | **300** | **183** | **61.0%** |

Merriam-Webster could rule on **183 of 300** stems. For comparison, stage 2 managed 4.5% and was abandoned on that basis. This one can be answered.

## The result

| Stratum | MW ruled | Comparative recognised | Not recognised | Rate (95% CI) |
|---|---:|---:|---:|---|
| WordNet adjective | 94 | 1 | 93 | 1.1% (0.2–5.8%) |
| WordNet noun/verb only | 46 | 0 | 46 | 0.0% (0.0–7.7%) |
| not in WordNet | 43 | 0 | 43 | 0.0% (0.0–8.2%) |
| **Total** | **183** | **1** | **182** | **0.5% (0.1–3.0%)** |

**Of 183 stems Merriam-Webster could rule on, it recognises the comparative for 1.**

Weighting each stratum by its share of the 8,809 stems gives **0.21%** — on the order of 18 stems, and perhaps 34 of the 16,478 forms, that a dictionary would accept.

That extrapolation assumes the stems MW could not rule on behave like those it could, within their stratum. It is least safe for *not in WordNet*, where coverage is lowest — but those are also the most obscure stems, so if the assumption fails it most likely flatters the generator rather than the reverse.

## What it got right

- **`blameworthy`** → `blameworthier blameworthiest` — MW lists these among its inflections.

A real gradable adjective, produced by the same blind affixation that produced the rest. The generator was not right on purpose.

## What it got wrong

MW enumerates each stem's real inflections and simply does not include the comparative:

| Stem | Synthetic forms | What MW actually lists |
|---|---|---|
| `abacterial` | `abacterialer abacterialest` | abacterial |
| `attemptable` | `attemptabler attemptablest` | attempt attemptable attempted attempting attempts |
| `bonhomous` | `bonhomouser bonhomousest` | bonhomie bonhomies bonhomous |
| `breathable` | `breathabler breathablest` | breathabilities breathability breathable |
| `castable` | `castabler castablest` | cast castabilities castability castable casting casts |
| `closeable` | `closeabler closeablest` | closable close closeable closed closes closing |
| `disfurnish` | `disfurnisher` | disfurnish disfurnished disfurnishes disfurnishing disfurnishment disf |
| `downloadable` | `downloadabler downloadablest` | download downloadable downloaded downloading downloads |

Excluded: 4 ruled by a source with no inflection list (Free Dictionary), 0 lookup errors. Neither counts as an answer.

