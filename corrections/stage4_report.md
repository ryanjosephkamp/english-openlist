# Stage 4 — are the remaining synthetic forms real?

300 stems sampled from the 42,290 behind the 45,723 forms they cover.

**No word was moved.** This stage measures.

The question is not whether Merriam-Webster carries the inflected form as a headword — it never would. It is whether MW lists that form among the inflections of its stem, in `meta.stems`. A "no" there is the dictionary enumerating a word's forms and leaving this one out.

## Coverage — can the question be answered at all?

| Stratum | Stems | Sampled | MW ruled | Coverage |
|---|---:|---:|---:|---:|
| plural / 3rd person | 28,594 | 120 | 11 | 9.2% |
| plural of a gerund | 8,736 | 80 | 58 | 72.5% |
| past tense or gerund | 4,616 | 70 | 28 | 40.0% |
| plural of an agent noun | 344 | 30 | 23 | 76.7% |
| **Total** | **42,290** | **300** | **120** | **40.0%** |

Merriam-Webster could rule on **120 of 300** stems. For comparison, stage 2 managed 4.5% and was abandoned on that basis. This one can be answered.

## The result

| Stratum | MW ruled | Inflection recognised | Not recognised | Rate (95% CI) |
|---|---:|---:|---:|---|
| plural / 3rd person | 11 | 4 | 7 | 36.4% (15.2–64.6%) |
| plural of a gerund | 58 | 0 | 58 | 0.0% (0.0–6.2%) |
| past tense or gerund | 28 | 0 | 28 | 0.0% (0.0–12.1%) |
| plural of an agent noun | 23 | 0 | 23 | 0.0% (0.0–14.3%) |
| **Total** | **120** | **4** | **116** | **3.3% (1.3–8.3%)** |

**Of 120 stems Merriam-Webster could rule on, it recognises the inflection for 4.**

Weighting each stratum by its share of the 42,290 stems gives **24.59%** — on the order of 10398 stems, and perhaps 11242 of the 45,723 forms, that a dictionary would accept.

That extrapolation assumes the stems MW could not rule on behave like those it could, within their stratum. It is least safe for *plural / 3rd person*, where coverage is 9.2% — and that stratum carries 68% of the population, so the weighted figure leans heavily on its few rulable stems.

## What it got right

- **`bioterrorism`** → `bioterrorisms` — MW lists these among its inflections.
- **`defamiliarization`** → `defamiliarizations` — MW lists these among its inflections.
- **`ebullism`** → `ebullisms` — MW lists these among its inflections.
- **`ferroelectricity`** → `ferroelectricities` — MW lists these among its inflections.

Produced by the same blind affixation that produced the rest. The generator was not right on purpose — but it was right.

## What it got wrong

MW enumerates each stem's real inflections and simply does not include the one the generator produced:

| Stem | Synthetic forms | What MW actually lists |
|---|---|---|
| `angry` | `angriers` | angrier angriest angrily angriness angrinesses angry |
| `barky` | `barkiers` | barkier barkiest barky |
| `chesty` | `chestiers` | chestier chestiest chesty |
| `cliquy` | `cliquiers` | clique cliques cliquey cliquier cliquiest cliquish cliquishly cliquish |
| `discreet` | `discreeters` | discreet discreeter discreetest discreetly discreetness discreetnesses |
| `distinct` | `distincters` | distinct distincter distinctest distinctly distinctness distinctnesses |
| `drossy` | `drossiers` | dross drosses drossier drossiest drossy |
| `flappy` | `flappiers` | flappier flappiest flappy |

Excluded: 2 ruled by a source with no inflection list (Free Dictionary), 0 lookup errors. Neither counts as an answer.

