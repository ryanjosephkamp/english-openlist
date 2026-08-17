# PROTOCOL

How the English OpenList is measured.

Every validation decision in the current dataset answers one question — *does
source X list this string?* That question has no defensible answer, because
choosing X is a judgement call and no source covers the space. This protocol
replaces it with a different question, and fixes the method for answering it
before any of the method runs.

**Word-ness is a latent binary variable. Every dictionary, word list and corpus
is a noisy detector of it, with its own sensitivity and specificity, and those
rates are estimable from the detectors' agreement structure with no ground
truth.** Nobody decides whether Wiktionary is credible; the model estimates it.

This document is written first and changed only by an entry in
`research/DECISIONS.md`. Numbers quoted here were measured on 2026-08-16 by the
commands recorded in `research/FEASIBILITY.md`; none is an estimate unless it
says so.

**Nothing in Phases 0–4 moves a word.** The live list, the site and the nightly
pipeline are untouched until Phase 5.

---

## 1. The operational definition

> **A string is a word of English if and only if it has attested, conventional,
> independent use in English text by multiple unrelated authors, and satisfies
> the form rules in §1.3.**

This is the latent variable. Everything downstream is conditional on it.

### 1.1 Why usage and not lexicography

Under a lexicographic definition — *a word is what a dictionary lists* —
dictionaries **are** the ground truth, the latent-variable model collapses into
"ask Merriam-Webster", and the programme walks back into the wall that stopped
the previous one: MW has no entry for 95.8% of one cluster and covers 9.2% of
the stems behind the synthetic plurals.

Under a usage definition, dictionaries are measurements of something outside
themselves. That is what makes the statistics non-circular and the result worth
publishing.

### 1.2 Three consequences, written down so they are not renegotiated

- **"Multiple unrelated authors" excludes nonce forms, single-author coinages
  and OCR artifacts, without excluding rare or technical vocabulary.** A word
  used once, by one person, in one place, is not yet a word of English. A word
  used by four chemists in four papers is, whether or not anyone has printed a
  dictionary entry for it.
- **Inflected forms count if they are independently used.** This is where the
  synthetic-intake problem lives, and the definition turns it from a policy
  argument into a measurable question: not *does MW list `advertings`* but *how
  productive is this affix on this class of stem, measured*.
- **Dictionary presence is strong evidence and never definitional.** A string
  absent from every dictionary can clear the bar. A string listed in one can
  fail it.

### 1.3 The form rules

**Changed 2026-08-16 by the dataset owner. The EOL is no longer Scrabble-conformant,
narrowly and deliberately.** See `research/DECISIONS.md` D-025.

| Rule | Implementation |
|---|---|
| lowercase ASCII letters only | `^[a-z]+$` |
| length | **no bound** |

That is the whole rule. The former bounds — minimum 2 characters, maximum 45 —
were inherited from Scrabble tournament dictionaries, and both excluded strings
that are words of English under §1's definition:

- **The 2-character minimum excluded `a` and `i`**, which are unambiguously
  English words. No Scrabble list can contain them: ENABLE, SOWPODS, NWL2023 and
  CSW21 hold **zero** one-letter entries between them, by rule rather than by
  judgement.
- **The 45-character maximum excluded attested chemistry.**
  `phosphoribosylaminoimidazolesuccinocarboxamide` is 46 characters and carries a
  Wiktionary English entry. Chemical nomenclature is productive and has no natural
  ceiling, so any numeric limit is arbitrary.

Since the goal is the largest defensible list of English words rather than a
Scrabble-legal one, the bounds go. **This admits no garbage**: the four
over-length strings on the invalid list are Welsh, Māori and Fijian place names,
and they are excluded by being proper nouns, which is a semantic judgement for
adjudication (gate G4) and was never what the length rule was doing.

**An ingest-time integrity flag replaces the ceiling.** Any candidate longer than
100 characters is flagged at ingest and requires a recorded reason before it
enters the frame. This is a data-integrity check against concatenation bugs, not
a form rule, and it is recorded as such. The longest candidate in the universe
today is 63 characters; **nothing currently exceeds 100**.

**One rule that was never implemented at all: "no proper nouns."**
`ProperNounDetector.is_likely_proper_noun` returns `False` for every lowercase
string; the class exists but does no work on the data as it arrives. Proper
nouns are therefore excluded only insofar as they are capitalised, and any
lowercase surname, place, brand or transliteration passes the form filter
untouched. Sampling the candidate set confirms this directly: `karpiak`,
`chetiyagiri`, `dowkaneh`, `benello`, `chaniadau` are all present.

This is why adjudication gate **G4** (§8.1) exists and why it carries more weight
than the other three. The protocol does not claim a rule the code does not
implement.

### 1.4 Edge cases

| Case | Ruling | Reason |
|---|---|---|
| Single letter | **candidate, adjudicated like anything else** | `a` and `i` are words; the rest are decided on evidence, not by me. Wiktionary cannot settle this — it assigns a word-level part of speech to 25 of 26 letters, including `q` as a determiner, so the lookup is uninformative and the four gates must do the work. |
| String over 45 characters | **candidate** | The ceiling was a Scrabble artifact. Chemical nomenclature is productive and unbounded. |
| Technical/taxonomic/chemical vocabulary | **word**, if independently used | The definition is usage, not general currency. `dicarboxylation` is used by chemists. |
| Inflected form of an attested stem | **word** if independently used; not automatically | Productivity is measured (§3.2), not assumed. |
| Archaic and obsolete forms | **word** | Attested use is attested use. The definition carries no tense. |
| Dialect and regional forms | **word** | "English" is not "standard written British or American English". |
| Lowercase form of a proper noun | **not a word**, unless it has separate common-noun use | `hoover` (to vacuum) qualifies; `benello` does not. Gate G4. |
| Abbreviation or acronym written lowercase | **not a word** unless lexicalised | `radar` and `laser` qualify; `asap` is adjudicated on use. |
| OCR corruption of a real word | **not a word** | `schoolinaster` is a scanning error, however often it recurs. This is the hardest class and §4 spec S5 models it explicitly. |
| Other-language string passing `^[a-z]+$` | **not a word of English** | `agiler` has a Wiktionary page because it is German. The `== English ==` confirmation is mandatory. |
| Space-loss concatenation | **not a word** | `modelsbasedon` is three words and a failed scan. |
| Single-author coinage | **not a word** | Fails "multiple unrelated authors" by construction. |

---

## 2. Sources

### 2.1 The candidate universe

The current dataset contributes **exactly one thing**: the candidate strings.
Every label, source attribution and confidence score in it is discarded and
re-derived from primary sources.

| Quantity | Count |
|---|---:|
| `merged_valid_words.txt` — raw lines | 345,297 |
| `merged_invalid_words.txt` — raw lines | 9,308,855 |
| **raw universe (line count)** | **9,654,152** |
| form-valid under `^[a-z]+$` | **9,653,962** |
| outstanding form violations | 190 (188 hyphenated, 2 accented) |

**The two universe figures are not interchangeable and the protocol must not
conflate them.** 9,654,152 counts lines; 9,653,962 counts strings that satisfy
§1.3. The 190-string difference is a known defect being cleared through
`corrections/ledger_form_rules.csv`, after which the two converge.

The universe is **frozen at a pinned Hugging Face revision**, not at "the current
dataset". The nightly pipeline promotes roughly 1,000 words per night from the
invalid list using Merriam-Webster, so the valid/invalid split moves every day
even when the universe does not. Phase 1 records the pinned revision in
`sources/MANIFEST.toml` and every later phase reads that revision alone.

### 2.2 The source list

Every source is ingested from a pinned, checksummed artifact recorded in
`sources/MANIFEST.toml`, so the evidence matrix reproduces byte-for-byte from
the manifest alone. Sizes below were probed on 2026-08-16.

**Lexicographic**

| Source | Artifact | Size | Notes |
|---|---|---:|---|
| WordNet 3.0 | nltk corpus, installed | — | 77,477 lemmas matching `^[a-z]{2,45}$` |
| Wiktionary titles | `enwiktionary-latest-all-titles-in-ns0.gz` | 27.8 MB | 4,416,714 a–z titles, **all languages** |
| Wiktionary articles | `enwiktionary-latest-pages-articles.xml.bz2` | 1.62 GB | streamed; source of the `== English ==` confirmation |
| web2 | `/usr/share/dict/words` | 2.5 MB | Webster's Second International, 1934; 234,428 a–z entries; public domain |
| hunspell en_US | LibreOffice `dictionaries` | 0.55 MB | `.dic` + `.aff`; expanded with `spylls` — see §3.1 |
| hunspell en_GB | " | 1.23 MB | " |
| hunspell en_CA | " | 0.55 MB | " |
| hunspell en_AU | " | 0.55 MB | " |

**Word lists**

| Source | Artifact | Size | Licence |
|---|---|---:|---|
| ENABLE1 | `dolph/dictionary` | 1.74 MB | public domain |
| SOWPODS (legacy) | mirrored plain list | 2.71 MB | freely mirrored |
| SCOWL 2020.12.07 | SourceForge tarball | 2.57 MB | permissive; ten nested size tiers |
| NWL2023 | `scrabblewords/scrabblewords` | 7.56 MB | **proprietary (NASPA)** |
| CSW21 | `scrabblewords/scrabblewords` | 12.58 MB | **proprietary (Collins)** |

**Corpus**

| Source | Artifact | Size | Notes |
|---|---|---:|---|
| wordfreq 3.1.1 | PyPI wheel | 56.8 MB | pre-aggregated over Wikipedia, subtitles, news, books |
| Google Books 2020 eng 1-grams | 24 shards | 24 × ~265 MB ≈ 6.4 GB | streamed one shard at a time; **carries `volume_count`, which the Ngram Viewer API does not expose** |

**Wiktionary's title index is a screen, not a verdict.** A title exists if *any*
language uses that spelling. English must be confirmed separately, over the API
or from the article dump, and this is mandatory rather than optional — `agiler`
is the standing counter-example.

### 2.3 Declared dependencies

Conditional independence is the main threat to validity in Dawid–Skene. Every
known derivation is declared **before** fitting, and specification S2 carries an
explicit interaction term for each.

| Edge | Nature |
|---|---|
| NWL / TWL ← OSPD ← Merriam-Webster | direct descent |
| ENABLE ↔ NWL | shared ancestry |
| hunspell en_US ← SCOWL | direct derivation |
| SCOWL tier 10 ⊂ 20 ⊂ … ⊂ 95 | nested by construction |
| hunspell en_GB / en_CA / en_AU ↔ en_US | shared upstream |
| wordfreq ← Google Books, Wikipedia, subtitles | wordfreq aggregates over corpora that are separately ingested |

**SCOWL's ten tiers are perfectly nested and must not enter as ten binary
detectors.** They enter as a single ordinal covariate — the smallest tier
containing the string, or ∞.

### 2.4 The dependency the model cannot express as an interaction

Sampling the stratum with no lexicographic evidence returns OCR wreckage:
`schoolinaster`, `modelsbasedon`, `stnven`, `iscences`, `amountes`, `terlopers`.
**The candidate universe was built from scanned text. So was Google Books.**

Querying Google Books directly:

| String | What it is | Peak rel. frequency | Nonzero years |
|---|---|---:|---:|
| `schoolinaster` | OCR of *schoolmaster* | **4.79e-08** | **168 / 220** |
| `iscences` | OCR fragment | 7.98e-09 | 186 / 220 |
| `amountes` | OCR of *amounts* | 8.94e-09 | 160 / 220 |
| `phlebothromboses` | real, medical | 1.88e-09 | 74 / 220 |
| `dicarboxylation` | real, chemistry | 1.12e-09 | 71 / 220 |

**The OCR artifacts outrank the genuine technical vocabulary on frequency and on
year-spread simultaneously.** No threshold on either separates them.

This is not conditional dependence between two detectors, which §4 S2 handles.
It is dependence between a detector and the process that generated the sampling
frame, and the log-linear family has no term for it: it would be absorbed
silently into an inflated prevalence and an inflated corpus specificity.

It is declared in the manifest as `frame_dependency = true`, and it is the reason
specification **S5** exists.

### 2.5 Normalization, pinned

Counts move with the filter, so the filter is part of the protocol rather than an
implementation detail.

**The pinned normalization is, verbatim and identically in `PROTOCOL.md`,
`CLAUDE.md` and `sources/MANIFEST.toml`:**

> `NFC; casefold; accept iff ^[a-z]+$`

**The rule change of §1.3 removed a tripwire ambiguity rather than adding one.**
Under the former `^[a-z]{2,45}$` filter, WordNet ∩ valid came to 57,967, while the
looser `isalpha() and isascii()` gave 57,977 — a 10-word drift caused entirely by
the length bounds. Under `^[a-z]+$` the two filters agree exactly: **77,503**
WordNet lemmas and **57,977** in the intersection. The tripwire is now
filter-independent for every source that contains no digits or non-ASCII.

Applied identically to every source and to the candidate universe.
`sources/MANIFEST.toml` records it per source, and a source whose ingest does not
reproduce its declared `record_count` is a hard failure, not a warning.

---

## 3. Evidence and features

### 3.1 Layer 1 — the evidence matrix

`E[word, source] ∈ {0,1}` over all 9,654,152 candidates and K sources, built by
streaming ingest, stored as parquet. Raw dumps are hashed and deleted; the
manifest makes them re-fetchable.

**hunspell requires an expansion step and the choice is recorded.** A `.dic` file
is stems plus affix flags, not a word list, so "hunspell lists X" is ambiguous
between *X is a stem* and *X is generated by a stem and an affix rule*. No
hunspell binary is installed. The protocol expands `.dic` + `.aff` to surface
forms using `spylls` (1.51 MB, pure Python, no binary dependency), and
`MANIFEST.toml` records `expansion = "spylls"` so the ambiguity is resolved in
writing rather than in code nobody reads.

**Corpus sources are not binarised on raw frequency.** §2.4 is the reason. They
enter as features (§3.2) and, where a binary column is needed, the threshold is
on **volume-level dispersion**, declared in advance in the manifest and reported
with a sensitivity analysis.

### 3.2 Layer 2 — features

Continuous evidence channels. These are detectors like any other and enter the
same model.

| Channel | Measures | Instrument |
|---|---|---|
| **Orthotactic plausibility** | P(string \| English spelling patterns) | character-level model: n-gram back-off first, small torch model only if it earns the complexity |
| **Morphological productivity** | is this a legal derivation of an attested stem by a *measurably* productive process | Baayen's **P = n₁/N**, hapax ratio per affix, computed on corpus data |
| **Dispersion** | usage spread across volumes, or concentrated | Gries's **DP**, Juilland's **D**, volume frequency, burstiness |
| **Zipf conformity** | does the frequency sit where a word of that rank should | deviation from a fitted Zipf–Mandelbrot curve |
| **Typed OCR neighbourhood** | is this string one known scanning confusion away from a commoner word | confusion pairs `m→in`, `rn→m`, `l→i`, `e→c`, `c→e`, `li→h`, applied directionally against a reference lexicon |

**The last channel exists because the obvious version of it does not work, and
that was measured rather than assumed.** Edit-distance-1 proximity to a reference
lexicon of WordNet ∪ web2 (deliberately not the current valid list):

| Stratum | Within edit-1 | 95% CI |
|---|---:|---|
| no lexicographic evidence, currently invalid | 34.6% | [34.0, 35.3] |
| no lexicographic evidence, currently valid | 17.8% | [17.3, 18.3] |
| control: currently valid and a Wiktionary title | **50.5%** | [49.8, 51.2] |

The signal separating the two candidate strata is large and its intervals do not
overlap — but it runs the wrong way against the control, because real words
cluster near other real words through inflection. **Raw edit distance is
confounded by morphology.** The typed, directional confusion pair is the
discriminating feature: `schoolmaster` → `schoolinaster` is exactly `m→in`.

### 3.3 Leakage discipline

The character model is trained only on strings held out of every evaluation set,
and never on anything whose label the model will later be asked to predict.
Train/test partitions are fixed by `sha256(seed:partition:word)` ranking, not by
a library RNG, so they are recomputable in any language and immune to stdlib
changes. Partition assignments are committed.

### 3.4 Why the feature layer is load-bearing rather than supplementary

Measured over the full candidate universe against three lexicographic detectors —
WordNet, Wiktionary titles, web2:

```
  wn/wkt/web2      valid      invalid         total   P(valid | pattern)
          111     48,668        3,004        51,672         0.9419
          110      8,701        3,205        11,906         0.7308
          101        397        3,230         3,627         0.1095
          100        201        5,507         5,708         0.0352
          011     42,005       57,577        99,582         0.4218
          010    159,033    1,015,890     1,174,923         0.1354
          001      3,383       41,897        45,280         0.0747
          000     82,909    8,178,545     8,261,454         0.0100
```

The pattern ordering is coherent, which is the first good sign for a latent-class
fit. But **8,261,454 strings — 85.57% of the universe — share the all-zero
cell**, and under conditional independence every one of them receives the same
posterior. Adding SCOWL, ENABLE, SOWPODS, hunspell and NWL barely dents it: they
are near-subsets of Wiktionary's 4.4M titles.

So the corpus arm and the feature layer are not decoration. They are the only
things that can say anything at all about 85% of the population — and the corpus
arm is the contaminated one. §7 attaches a stopping rule to exactly this.

*(The table above is also a preview of the Phase 4 held-out comparison. It is
reported here as a property of the sources. It is never fitted to.)*

---

## 4. Model specifications

Fitting is over **evidence patterns, not words**: with K sources there are at
most 2^K distinct patterns and far fewer observed, so 9.65M rows collapse to a
contingency table of a few thousand cells, EM runs in seconds, and the fit is
exactly reproducible.

| # | Specification | What it buys |
|---|---|---|
| **S1** | Conditional independence (classic Dawid–Skene) | The baseline that is almost certainly wrong, fitted so its wrongness is *measured* rather than assumed. |
| **S2** | Log-linear with declared interactions (Espeland & Handelman) | Pairwise terms for every edge in §2.3. |
| **S3** | Random-effects latent class (Qu, Tan & Kutner) | A per-word latent difficulty absorbing residual dependence. |
| **S4** | Feature-augmented | Layer 2 channels as continuous covariates on the latent class. The first spec that can distinguish two members of the all-zero cell. |
| **S5** | **Three-class with an OCR nuisance class** | Latent classes `{real word, OCR-artifact, neither}`. The OCR class is anchored by the typed-confusion channel (§3.2) and characterised by high corpus presence with near-zero lexicographic presence. |

**S5 is the response to §2.4.** Without it the frame dependency is absorbed into
prevalence and corpus specificity and never seen again. With it, the
contamination is a parameter with an estimate and an interval.

**Selection is by BIC *and* by recovery in the simulation study, never by BIC
alone.** A specification that wins on BIC but fails to recover known parameters
in simulation at the observed sparsity is rejected, and that rejection is
reported.

The same log-linear machinery, with the all-zero cell as the target, gives the
**capture–recapture population estimate** — how many words no source caught. It
is reported with its caveat and not without it: heterogeneous capture probability
biases multiple-systems estimation downward, so the figure is a **lower bound**
on English vocabulary and is stated as one.

---

## 5. The identifiability check

Run before any result is believed. A model that cannot identify its parameters is
**reported as non-identified, not fitted anyway.**

**5.1 Degrees of freedom.** 2^K − 1 free cells against the parameter count: 2K+1
under S1, plus one term per declared interaction under S2, plus 3K+2 under S5.
At K ≥ 10 this is not the binding constraint — 2^15 − 1 = 32,767 cells against a
few hundred parameters — and the protocol says so rather than presenting a
satisfied inequality as if it settled the question. **The binding constraints are
5.2–5.5.**

**5.2 Rank and conditioning.** Numerical rank and condition number of the
observed Fisher information at the optimum. The threshold is declared before
fitting; a condition number above it is a failure, not a caveat.

**5.3 Profile likelihood.** Computed for every α_k and β_k. **A flat profile means
the parameter is not identified**, regardless of what the optimiser returned.

**5.4 Multi-start.** EM from at least 50 random initialisations. All runs must
reach the same optimum modulo label switching; divergence is a failure.

**5.5 Simulation recovery at the observed sparsity.** Not at a convenient one.
The synthetic worlds are generated with the pattern-frequency profile actually
observed in Phase 1, including an all-zero cell of the measured size.

### Two structural problems, and their fixes

**Label switching.** Two-class LCA is identified only up to relabelling, and
three-class worse. Fixed by an anchor constraint: a designated reference source
is constrained to α + β > 1, which orients the classes. For S5 the OCR class is
additionally oriented by requiring its mean typed-confusion score to exceed the
other classes'. Both constraints are declared before fitting.

**Boundary solutions.** A source that behaves near-perfectly in the observed
table drives α or β to 1, which makes the information matrix singular and 5.2
undefined. Fixed by weakly informative Beta priors (penalised EM / MAP), with
hyperparameters fixed in advance and a sensitivity analysis over them reported
alongside the fit.

---

## 6. Evaluation design

Four checks. Three need no human at all.

### 6.1 Simulation study — mandatory

Generate synthetic worlds with known sensitivities, specificities, prevalence and
dependence structure; fit; check the estimator recovers them. **A methods paper
without this is not a methods paper.** It is also the only way to learn how badly
mis-specified dependence hurts, which is the question S1 exists to answer.

### 6.2 Held-out-source recovery

Hide one source entirely, refit, ask whether the model predicts its membership.
Repeat per source. Measures generalisation with no labels required.

### 6.3 Negative controls — four families

| Family | Construction | Role |
|---|---|---|
| **OCR corruptions** | Real words corrupted by the typed confusion patterns of §3.2 | **Primary validity check on the corpus arm**, not one test among four — see §2.4 |
| Pseudo-words | Sampled from the character model, matched on length and n-gram distribution | Hard negatives by construction |
| Other-language strings | Non-English strings passing `^[a-z]+$` | The `agiler` failure mode |
| MW-refuted inflections | 441 forms where MW ruled on the stem and did not list the form | Real, already-adjudicated negatives |

**The MW-refuted family is 441 deduped forms**, taken from rows with
`outcome = inflection-absent` in `corrections/ledger_stage3.csv` and
`ledger_stage4.csv` — not the ~298 previously estimated. 434 are currently on the
invalid list and 7 are still on the valid list, which is itself a finding to
report.

### 6.4 Calibration

**This never decides whether a word is valid.** It is the only way to learn
whether P = 0.8 actually means 80%, and without it the output probabilities are
uninterpretable.

**Sample.** 1,500 items, blind, stratified by posterior decile with **equal
allocation** — 150 per decile. Equal rather than proportional allocation because
the object is a reliability diagram, which wants comparable precision in every
bin, not an efficient estimate of the mean. At 150 per bin a Wilson interval is
roughly ±8 points at p = 0.5.

**Reported as** a reliability diagram and expected calibration error, with
per-bin Wilson intervals.

**The adjudicator is a detector, not the ground truth.** Ryan's labels are a
noisy reading of the latent variable with sensitivity α and specificity β, so the
observed per-bin rate is

    observed = (1 − β) + p(α + β − 1)

and the true rate p is recovered by the **Rogan–Gladen correction**, valid
whenever α + β > 1.

**Anchors.** α and β have no inputs without them. 120 anchor items — 60
unambiguous positives (high-frequency common words) and 60 machine-generated
pseudo-words verified absent from every source — shuffled in unmarked and
indistinguishable from the calibration sample.

**Anchors are easy items, so α and β estimated from them are optimistic.** The
corrected curve is therefore reported as a **sensitivity band across a plausible
α, β range, never as a point estimate**, and the limitation is stated in the
paper rather than in a footnote.

**Self-consistency.** 150 items from the calibration sample re-presented later in
the session order, unmarked. Reported as Cohen's κ.

**Total presentations: 1,770** (1,500 + 120 + 150).

**Budget, corrected.** The 2026-08-16 rehearsals measured 20.1 s/item overall but
**30.4 s/item on searched items against 9.8 s unsearched**. Since §8.3 makes
searching mandatory, the applicable rate is 30.4 s/item, giving **≈ 14.9 hours**,
not the ≈ 9 hours implied by the blended figure. The always-search rule is
bought, not free, and the price is stated here so it is not discovered in Phase 4.

### 6.5 The LLM arm

An LLM judge runs as a **parallel arm whose agreement with the human adjudicator
is reported as a result**. It is never the reference standard: its lexical priors
derive from Wiktionary and the dictionaries that are themselves detectors in this
model, so its errors are correlated with the sources by construction.

Three legitimate roles: pre-filtering retrieved snippets for use-vs-mention (it
judges supplied text, not lexical memory); one more declared detector in the
latent-class model, with its dependencies declared like any other; and an
independent arm over the same items, answering *can this be automated next time*
with evidence instead of opinion.

### 6.6 The current valid list

**Held out as a test set. Never a fitting target.** Fitting to it would make the
haphazard verdicts being replaced into the target the replacement reproduces.

Measure the agreement rate, investigate the disagreements. High agreement
validates a year of prior work. Disagreements are findings — some will be errors
the old method made, some errors the new one makes, and separating those is the
research.

**The test set drifts.** The nightly promotes ~1,000 words/night using MW, so the
held-out labels are being continuously reshaped by an MW-based process. The
comparison is made against the **pinned revision** of §2.1 and reports that
revision's date.

---

## 7. Success criteria and stopping rules

Each rule is written before the measurement it governs runs. Stage 2 of the
previous programme is the precedent: its rule fired, the method was declared
unsound, and no queue was handed over on a 63–99% interval.

| # | Rule | Trigger |
|---|---|---|
| **SR1** | **Halt the calibration phase if anchor α + β ≤ 1.** | Rogan–Gladen is undefined and the adjudicator is not a usable detector. |
| **SR2** | **Halt if the corpus arm does not break the all-zero stratum.** After full ingest, no single evidence pattern may hold more than **50%** of the candidate universe. | Above that, the majority of the population shares one posterior and per-word probabilities are not a meaningful output. Currently **85.57%**. |
| **SR3** | **Halt if the OCR negative-control family is not separated.** | If corpus-detector specificity on OCR-corrupted real words is statistically indistinguishable from its specificity on rare real words, the corpus arm is measuring scan artifacts and must be reported as such rather than fitted. |
| **SR4** | **Halt if the identifiability check fails** on the selected specification — flat profile likelihood, singular information, or multi-start divergence. | Report as non-identified rather than fitting anyway. |
| **SR5** | **Halt if simulation recovery falls outside the pre-stated tolerance.** | No real-data result is believed before the estimator is shown to recover known parameters at the observed sparsity. |

**Success criteria**

- The evidence matrix reproduces from `MANIFEST.toml` alone on a clean machine,
  with matching per-source counts.
- Every fit is deterministic: same evidence file, same specification, same seed,
  same posteriors, verified by re-running.
- The selected specification passes all five identifiability checks.
- Expected calibration error falls within the bound pre-registered after the
  Phase 3 pilot.
- Sampled quantities always carry intervals. **No sampled figure is ever reported
  as a count.**

**Pre-registration lands between the Phase 3 pilot and Phase 4** — after the
evidence layer exists and the model has run on a held-out slice, so the
confirmatory design is frozen against a structure known to be identifiable rather
than a hoped-for one.

---

## 8. The adjudication protocol

**Verdicts bind to the state of the evidence, never to how plausible a word
feels.**

### 8.1 The four gates for what counts as a use

All four must pass. A hit that fails any one of them is not a use.

| Gate | Test | Why |
|---|---|---|
| **G1 — use, not mention** | The string works *in* a sentence, rather than being listed, defined or discussed. | Kills word-list SEO pages and dictionary entries in one move. A definition is a mention by construction. |
| **G2 — two independent authors** | Two occurrences by people with no shared origin. Mirrors, reposts, quotations and syndicated copies are **one** author. | This is the definition's core. One author is a coinage. |
| **G3 — conventional** | No gloss, no scare quotes, no "so-called", no nonce-marking. | An author flagging the word as novel is evidence it is not yet conventional. |
| **G4 — common word, not a name** | An occurrence as a surname, place, brand or title does not attest a lowercase common word. | Added after a rehearsal accepted the machine-generated pseudo-word `brimsel` at 43 seconds, almost certainly on a proper-noun hit. §1.3 is why this gate has to do the work the form rules do not. |

### 8.2 Search instruments, in fixed order

**90-second budget per item.**

1. **Google Books** — first, deliberately. Books are authored and edited by
   construction, carry author/title/date for the G2 independence check, show
   snippet context for the G1 call, and carry almost no word-list spam.
2. **Google Scholar**
3. **PubMed / PMC** — for the `-oses` medical plurals in particular
4. **HathiTrust**
5. **Filtered web search**, last, with detector sources and word-list domains
   excluded

`wordfreq` and the Ngram Viewer are **triage aids, not evidence**. They say a
string occurs; they cannot pass G1, G2, G3 or G4.

### 8.3 Search conduct

The forbidden-source rule is about **sources**, not search engines. The protocol
constrains what counts as evidence, not where you look. Three rules, all found
empirically in rehearsal:

- **`define X` queries are banned.** That query form is engineered to return
  dictionary definitions, which fail two gates at once: forbidden source, and a
  mention by construction. Query forms that hunt for the string in running text —
  `"most permissive" OR "permissivest"` — are the correct shape.
- **AI-generated search summaries must be ignored.** They synthesise from sources
  *including* the forbidden dictionaries, so contamination arrives invisibly with
  no citation to check; they are an LLM, which reintroduces the LLM-as-judge
  circularity through the back door; and they can assert attestations that do not
  exist. Search results now carry one by default, so this is a live hazard on
  every query.
- **Escalating past the listed instruments is allowed and recorded** as a
  distinct state, so escalated items can be checked for differential calibration.

**Searching is never skipped, and the tier is observed rather than declared.**
Skipping the search on confident-feeling items would make the adjudicator's
errors correlate with the model's own inputs precisely in the high-probability
bins where the threshold lands, breaking the independence the Rogan–Gladen
correction assumes. The app records *whether a search was opened* automatically;
calibration is computed within tier and compared, so residual fast-path bias is
measurable instead of hidden.

**A search returning nothing is the safe case. A search returning *something* is
where the gates do the work.** Do not treat "I found hits" as sufficient.

### 8.4 The verdict table

| Verdict | Condition |
|---|---|
| **yes** | ≥ 2 independent conventional uses passing all four gates — **or** one use in an editorially reviewed source, since author plus editor is already two people accepting it |
| **no** | The protocol ran to completion and found zero qualifying uses |
| **unsure** | Exactly one qualifying use, **or** the item could not be adjudicated within the budget |

**`no` asserts only that a bounded 90-second protocol found fewer than two
qualifying uses. It never asserts that the string is not a word.** Every verdict
in this project is a statement about the evidence reachable on a date.

### 8.5 What the adjudication app must guarantee

Built in Phase 1, because it depends on the sample rather than the model, and
building it under Phase 4 pressure is how corners get cut.

**Its one hard requirement is that the work is never repeated.** Append-only
JSONL; `fsync` before the UI advances; state derived by replay rather than
stored; committed and pushed to the private `eol-archive` after each session;
resumable elsewhere by clone-and-replay.

- **Blinding** is enforced by the app holding the stratum mapping and never
  rendering it. Anchors are indistinguishable from calibration items.
- **The timer is soft.** It warns at 45 minutes and never cuts mid-item.
- **Records per presentation:** item id, verdict, milliseconds, whether a search
  was opened, which instrument, whether escalation occurred, session id,
  timestamp.

---

## 9. Governance

Five mechanisms against hallucination and drift, in descending order of leverage.

1. **Every number comes from code.** No figure appears in any document unless a
   committed script produced it and can regenerate it. Enforced by a check that
   re-derives the numbers quoted in markdown and fails on mismatch. A
   hallucinated statistic cannot survive this.
2. **`CLAUDE.md`**, loaded automatically each session: the definition, the
   `candidate_source` prohibition, the never-write rule, and the tripwire counts
   *with the normalization that produces them*.
3. **A stopping rule written before every measurement runs** (§7).
4. **Append-only `research/DECISIONS.md`** — every methodological choice, dated,
   with rationale. Prevents silent re-litigation and writes the methods section
   as a side effect.
5. **Determinism everywhere.** Sampling by `sha256(seed:stratum:word)` ranking
   rather than a library RNG — recomputable in any language, immune to stdlib
   changes.

**`candidate_source` is a discovery log and is never evidence.** It credits
WordNet for 2,127 words; the real intersection is 57,977, a 27× undercount. It
records where a candidate was first *seen*, not which sources *contain* it. Any
evidence model built on it measures the wrong quantity.

---

## 10. What this protocol does not claim

- It does not decide any word. It defines how words are measured.
- It does not choose the release threshold. That is the one human choice left,
  and it is stated openly and published at several values.
- It does not declare any source credible. Every source's rates are estimated.
- The population estimate is a **lower bound**, not a count of English.
- `no` is a statement about a 90-second protocol on a date, not about English.
- **No word is ever permanently invalid.** Under this method that falls out for
  free: everything carries a probability and nothing carries a life sentence.
