# DECISIONS

**Append-only.** Every methodological choice, dated, with its rationale. Never
edit or delete an entry — if a decision turns out wrong, append a new one that
supersedes it and say why. This prevents silent re-litigation, and it writes the
paper's methods section as a side effect.

Format: `## D-nnn — title` / date / decision / rationale / status.

Status is `settled` (not open for re-argument), `provisional` (expected to be
revisited at a named phase), or `superseded by D-nnn`.

---

## D-001 — The definition is usage-based, not lexicographic

**2026-08-15** · settled

A string is a word of English **iff it has attested, conventional, independent
use in English text by multiple unrelated authors**, and satisfies the form rules
in `scripts/word_validator.py`.

**Rationale.** Under a lexicographic definition — *a word is what a dictionary
lists* — dictionaries **are** the ground truth, the latent-variable model
collapses into "ask Merriam-Webster", and the programme returns to the wall that
stopped its predecessor: MW had no entry for 95.8% of one cluster and covered
9.2% of the stems behind the synthetic plurals. Under a usage definition
dictionaries are measurements of something outside themselves, which is what
makes the statistics non-circular and the result publishable.

Three consequences follow and are written into `PROTOCOL.md` §1.2: nonce forms
and single-author coinages are excluded without excluding rare or technical
vocabulary; inflected forms count if independently used; dictionary presence is
strong evidence and never definitional.

---

## D-002 — The current dataset contributes only the candidate strings

**2026-08-15** · settled

Exactly one thing is inherited: the **9,654,152 candidate strings**. Every label,
source attribution and confidence score is discarded and re-derived from pinned,
checksummed primary sources.

**Rationale.** Measured, not assumed: `candidate_source` credits WordNet for
2,127 words, while the real intersection of the valid list with WordNet is
**57,977** — a 27× undercount. The field records where a candidate was first
*seen*, not which sources *contain* it. Separately, 209,053 of 345,297 valid
words (60.5%) carry no corpus attribution at all, and 176,124 entries hold
nothing but `source: twl_scrabble_dictionary`. An evidence model built on any of
this measures the wrong quantity.

---

## D-003 — `candidate_source` is a discovery log and is never evidence

**2026-08-15** · settled

`candidate_source` records where a candidate was first **seen**, not which
sources **contain** it. It is never read as evidence, and neither are the
`source` and `confidence` fields of `merged_valid_dict.json`.

**Rationale.** A direct corollary of D-002, recorded as its own entry because it
is the single easiest mistake for a future session to make: the field is named
like an attestation matrix, is shaped like one, and is not one. Carried in
`CLAUDE.md` §3 so it loads automatically every session rather than waiting to be
rediscovered.

---

## D-004 — The current valid list is a held-out test set, never a fitting target

**2026-08-15** · settled

**Rationale.** The instinct was to start from the currently-valid words and
ensure they stay valid. That is circular: it makes the haphazard verdicts being
replaced into the target the replacement is fitted to reproduce. Held out
instead, the agreement rate becomes a *result*. High agreement validates a year
of prior work; disagreements are findings, and separating "the old method erred"
from "the new method erred" is the research rather than an embarrassment.

---

## D-005 — Human adjudication calibrates the probabilities; it never decides a word

**2026-08-15** · settled

A blind stratified sample of ~1,500 words, plus ~120 anchor items (60
unambiguous positives, 60 verified pseudo-words) estimating the adjudicator's own
sensitivity α and specificity β, plus a re-adjudicated subset measuring
self-consistency.

**The adjudicator is a noisy detector, not the ground truth.** The observed
per-bin rate is `(1−β) + p(α+β−1)`; the true rate is recovered by the
**Rogan–Gladen correction**, valid whenever α+β > 1. Anchors are easy items, so
α and β from them are optimistic — the corrected curve is reported as a
**sensitivity band across a plausible α, β range, never a point estimate**.

**Rationale.** Accepted despite a standing objection to human judgement, because
it is measurement rather than verdict. It never decides whether a word is valid.
It is the only way to learn whether P = 0.8 means 80%, and without it the output
probabilities are uninterpretable.

---

## D-006 — Verdicts bind to the evidence; searching is never skipped

**2026-08-16** · settled

Verdicts bind to the state of the evidence, never to how plausible a word feels.
Searching is mandatory on every item, and the app records **whether a search was
opened**, so the confidence tier is observed rather than self-reported.

**Rationale.** Two rehearsals of 24 items each. Round one searched 2/24 and let
`agiler` — German — through in 1.9 seconds. Round two searched 12/24 and caught
3/3 traps. Skipping the search on confident-feeling items would make the
adjudicator's errors correlate with the model's own inputs precisely in the
high-probability bins where the threshold lands, breaking the independence the
Rogan–Gladen correction assumes. Calibration is computed within tier and
compared, so residual fast-path bias is measurable instead of hidden.

Measured: α = 4/4, β = 3/4, α+β = 1.75 on 4 anchors of each kind. The resulting
CIs — [0.51, 1.00] and [0.30, 0.95] — are the concrete argument for 60 of each
rather than a handful.

---

## D-007 — Four gates decide what counts as a use

**2026-08-16** · settled

**G1 use-not-mention** · **G2 two independent authors** · **G3 conventional** ·
**G4 common word, not a name**.

**Rationale.** G1 kills word-list SEO pages and dictionary entries in one move —
a definition is a mention by construction. G2 is the definition's core. G3
catches authors flagging a word as novel. **G4 was added after a rehearsal
accepted the machine-generated pseudo-word `brimsel` at 43 seconds**, almost
certainly on a proper-noun hit: it is absent from all 9M Wiktionary titles in
every language and has no one-edit neighbour on the valid list. The EOL's form
rules were supposed to exclude proper nouns; the adjudication gates did not, and
neither, it turns out, does the code (see D-013).

**A search returning nothing is the safe case. A search returning *something* is
where the gates do the work.**

---

## D-008 — Search conduct: no `define X`, ignore AI summaries, record escalation

**2026-08-16** · settled

- **`define X` queries are banned** — the form is engineered to return dictionary
  definitions, which fail two gates at once: forbidden source, and a mention by
  construction. Query forms that hunt for the string in running text are correct.
- **AI-generated search summaries must be ignored** — they synthesise from
  sources *including* the forbidden dictionaries, so contamination arrives
  invisibly with no citation to check; they are an LLM, which reintroduces the
  LLM-as-judge circularity through the back door; and they can assert
  attestations that do not exist. Search results carry one by default, so this is
  live on every query.
- **Escalating past the listed instruments is allowed and recorded** as a
  distinct state, so escalated items can be checked for differential calibration.

**Rationale.** All three were found empirically in the 2026-08-16 rehearsals
rather than derived from theory, which is why they are recorded as a decision
rather than left to the adjudicator's judgement in the moment. The common thread
is that each closes a route by which a **forbidden source reaches the verdict
without announcing itself** — a definition arriving through a query form, a
dictionary arriving through a generated summary, an unusual instrument arriving
without a trace in the record.

The forbidden-source rule is about **sources**, not search engines. The protocol
constrains what counts as evidence, not where you look.

---

## D-009 — LLM-as-judge is a parallel arm, never the reference standard

**2026-08-15** · settled

**Rationale.** Its lexical priors derive from Wiktionary and the dictionaries
that are themselves detectors in this model, so its errors are correlated with
the sources by construction, and reviewers reject it as a sole reference. Three
legitimate roles: pre-filtering retrieved snippets for use-vs-mention (judging
supplied text, not lexical memory); one more declared detector with its
dependencies declared like any other; and an independent arm over the same items
whose **agreement with the human adjudicator is reported as a result**. That
answers "can this be automated next time" with evidence rather than opinion.

---

## D-010 — Pre-registration lands after the Phase 3 pilot, not before Phase 1

**2026-08-15** · settled

Build the evidence layer, run the model on a held-out slice to learn whether the
sources overlap enough to identify the parameters, **then** freeze the
confirmatory design and timestamp it on OSF.

**Rationale.** Pre-registering earlier risks committing to a design that turns
out unidentifiable — and §5 of the protocol exists precisely because that is a
live possibility rather than a formality.

---

## D-011 — No paid APIs; everything runs locally; corpora are streamed

**2026-08-15** · settled

Streaming ingest, keep derived aggregates only, delete raw dumps after hashing.
The manifest makes everything re-fetchable, so nothing large is hoarded.

**Rationale.** ~12 GB of disk was free when this was decided; 14 GiB measured on
2026-08-16. It is also simply good practice: a pipeline that cannot stream cannot
be reproduced on a smaller machine.

---

## D-012 — A third latent class for OCR artifacts (specification S5)

**2026-08-16** · settled

The model carries a fifth specification with **three latent classes — `{real
word, OCR-artifact, neither}`** — the OCR class anchored by a **typed
OCR-confusion neighbourhood** channel (`m→in`, `rn→m`, `l→i`, `e→c`), not by raw
edit distance.

**Rationale, measured.** Sampling the stratum with no lexicographic evidence
returns OCR wreckage: `schoolinaster`, `modelsbasedon`, `stnven`, `iscences`,
`amountes`. **The candidate universe was built from scanned text, and so was
Google Books.** Querying the Ngram corpus directly (en-2019, smoothing 0):

| string | what it is | peak rel. freq | nonzero years |
|---|---|---:|---:|
| `schoolinaster` | OCR of *schoolmaster* | 4.79e-08 | 168/220 |
| `iscences` | OCR fragment | 7.98e-09 | 186/220 |
| `phlebothromboses` | real, medical | 1.88e-09 | 74/220 |
| `dicarboxylation` | real, chemistry | 1.12e-09 | 71/220 |

The OCR artifacts **outrank the genuine technical vocabulary on frequency and on
year-spread simultaneously**. No threshold on either separates them.

This is not conditional dependence between two detectors, which the log-linear
model handles with an interaction term. It is dependence between a detector and
the process that generated the **sampling frame**, which the log-linear family
cannot express at all, and which would otherwise be absorbed silently into an
inflated prevalence and an inflated corpus specificity. S5 makes it a parameter
with an estimate and an interval.

**The obvious cheaper fix was tested and rejected.** Edit-distance-1 proximity to
a reference lexicon of WordNet ∪ web2: 34.6% [34.0, 35.3] on the all-zero-invalid
stratum against 17.8% [17.3, 18.3] on all-zero-valid — a large, clean separation
— but **50.5%** [49.8, 51.2] on a control of currently-valid Wiktionary words.
Real words cluster near other real words through inflection, so raw edit distance
is confounded by morphology. The typed, directional confusion pair is what
discriminates: `schoolmaster` → `schoolinaster` is exactly `m→in`.

---

## D-013 — `word_validator.py` does not implement the proper-noun rule

**2026-08-16** · settled (recorded, not chosen)

The operative form rules are `^[a-z]+$` and length 2–45. **Nothing else.**
`ProperNounDetector` exists but `is_likely_proper_noun` returns `False` for every
lowercase string, so lowercase surnames, places, brands and transliterations pass
the filter untouched — `karpiak`, `chetiyagiri`, `dowkaneh`, `benello` and
`chaniadau` are all in the candidate set.

**Rationale.** This entry records a fact rather than making a choice, and it is
here because the gap between the documented rule and the implemented one is
load-bearing. Gate G4 (D-007) carries weight the form rules were assumed to
carry; `brimsel` slipped through a rehearsal on what was almost certainly a
proper-noun hit precisely because both layers were assumed to be covering it and
neither was. `PROTOCOL.md` therefore states the rules **as implemented** rather
than as documented.

No code is changed. This is Phase 0, which writes the method down and moves
nothing; whether to implement the missing rule is a Phase 5 question and gets its
own entry when it arrives.

---

## D-014 — Corpus arm: wordfreq plus raw Google Books 1-gram shards

**2026-08-16** · settled

Both. `wordfreq` 3.1.1 (56.8 MB wheel, **not currently installed**) and the 24
raw Google Books 2020 eng 1-gram shards (~265 MB each, streamed and deleted one
at a time, peak disk ~300 MB).

**Rationale.** Two measured facts force it.

First, **85.57% of the candidate universe — 8,261,454 strings — is all-zero on
WordNet, Wiktionary titles and web2**, and under conditional independence every
one of them receives an identical posterior. Adding SCOWL, ENABLE, SOWPODS,
hunspell and NWL barely dents it: they are near-subsets of Wiktionary's 4.4M
titles. The corpus arm and the feature layer are the only things that can say
anything at all about 85% of the population.

Second, **the raw shards are required because they carry `volume_count`**. The
Ngram Viewer API does not expose it, and volume-level dispersion is the only
signal left that can separate OCR noise from rare real words after D-012 ruled
out frequency and year-spread. `wordfreq` alone is cheap and clean but its
cleaning costs it sensitivity on exactly the technical tail that dominates the
all-zero-valid stratum.

**Never binarise Google Books on raw frequency.** Where a binary column is
needed, the threshold is on volume-level dispersion, declared in the manifest
before fitting and reported with a sensitivity analysis.

---

## D-015 — Proprietary word lists included, published in aggregate only

**2026-08-16** · settled

NWL2023 (NASPA, 7.56 MB) and CSW21 (Collins, 12.58 MB) enter as detectors.
`MANIFEST.toml` carries `redistributable = false` for both, meaning: per-source
sensitivity and specificity are published, the evidence-pattern table is
published, every model result depending on them is published — and the **raw
per-word column is not**. The reproducibility package ships a fetch script rather
than the data.

**Rationale.** Their lineage is genuinely distinct from Wiktionary's, so dropping
them costs real statistical power. The existing dataset already draws 176,124
entries from TWL, so this is a pre-existing condition rather than a new exposure
— but a published reproducibility package is a different artifact from a word
list on Hugging Face, and the distinction deserves respecting rather than
inheriting by default.

---

## D-016 — Author diversity is measured at adjudication, approximated at feature time

**2026-08-16** · settled

The definition (D-001) requires **multiple unrelated authors**. No obtainable
corpus supplies author metadata at feature scale, so:

- at **feature** time, author diversity is **approximated** by volume/document
  dispersion (Gries's DP, Juilland's D, volume frequency, burstiness), and the
  protocol calls it an approximation;
- at **adjudication** time it is measured **directly**, via Google Books' per-
  snippet author/title/date — which is why Google Books is the *first* instrument
  in the fixed search order rather than the fourth.

**Rationale.** OpenSubtitles' monolingual English file is 3.66 GB with no
document or author boundaries, so author diversity is not recoverable from it at
any disk cost. Gutenberg has the metadata but bulk retrieval is ~80 GB and its
operators discourage crawling. Wikipedia gives article boundaries, but a
Wikipedia article has no single author. Google Books' `volume_count` is volume
dispersion, not author dispersion — two volumes can share an author.

This is a real reduction in what the feature layer can claim. Recorded here so
the paper states it rather than a reviewer finding it.

---

## D-017 — Four stopping rules added to the one already specified

**2026-08-16** · settled

The programme carried one stopping rule: **halt if anchor α + β ≤ 1** (SR1). Four
more, each written before the measurement it governs:

- **SR2** — halt if the corpus arm does not break the all-zero stratum. After
  full ingest, **no single evidence pattern may hold more than 50%** of the
  candidate universe. Currently 85.57%. Above the threshold, the majority of the
  population shares one posterior and per-word probabilities are not a meaningful
  output.
- **SR3** — halt if the OCR negative-control family is not separated. If
  corpus-detector specificity on OCR-corrupted real words is statistically
  indistinguishable from its specificity on rare real words, the corpus arm is
  measuring scan artifacts and must be reported as such rather than fitted.
- **SR4** — halt if the identifiability check fails on the selected
  specification: flat profile likelihood, singular information matrix, or
  multi-start divergence. Report as non-identified rather than fitting anyway.
- **SR5** — halt if simulation recovery falls outside the pre-stated tolerance.

**Rationale.** Stage 2 of the previous programme is the precedent: its stopping
rule fired, the method was declared unsound, and no queue was handed over on a
63–99% interval. Every rule above names the measurement that triggers it, so none
of them can be argued away after the fact.

---

## D-018 — The candidate universe is frozen at a pinned HF revision

**2026-08-16** · settled

`sources/MANIFEST.toml` pins revision `ba94dd0d`. Every phase reads that revision
alone.

**Rationale.** The nightly pipeline promotes ~1,000 words per night from the
invalid list **using Merriam-Webster**, so the valid/invalid split moves daily.
Two things follow. "The current dataset" is not a reproducible object, so the
freeze must name a revision. And the held-out test set of D-004 is being
continuously reshaped by an MW-based process — which is the very process being
replaced — so the comparison must be made against the pinned revision and report
its date.

Measured on 2026-08-16: the local `.cache/hf/` snapshot is two nightly runs
behind live, differing by +14 bytes on the valid file and −14 on the invalid.

---

## D-019 — The pinned normalization is part of the protocol

**2026-08-16** · settled

**NFC, casefold, accept iff `^[a-z]{2,45}$`.** Applied identically to every
source and to the candidate universe, recorded per source in `MANIFEST.toml`.

**Rationale.** Counts move with the filter. WordNet ∩ valid is **57,977** under
`isalpha() and isascii()` but **57,967** under `^[a-z]{2,45}$`, because the
looser filter admits 1-character lemmas and lemmas longer than 45. A tripwire
that drifts with the filter is not a tripwire. Both figures are carried in
`CLAUDE.md` §4 so a future session checks the filter before concluding the data
changed.

---

## D-020 — The MW-refuted negative-control family is 441 forms, not ~298

**2026-08-16** · settled (correction)

Deduped across `corrections/ledger_stage3.csv` and `ledger_stage4.csv`, rows with
`outcome = inflection-absent` — MW ruled on the stem and did not list the form —
yield **441 distinct forms**. 434 are currently on the invalid list; **7 are
still on the valid list**, which is itself a finding to report rather than
quietly fix.

**Rationale.** The earlier figure of ~298 was an estimate carried forward through
several documents without being recomputed. This one is a count, and the entry
exists so the corrected figure has somewhere to live other than a diff.

The 7 forms still on the valid list are **not** silently corrected here. They are
carried into Phase 4 as reported disagreements between the old method and the
new, which is what D-004 says disagreements are for.

---

## D-021 — SCOWL enters as one ordinal covariate, not ten binary detectors

**2026-08-16** · settled

Value = the smallest tier containing the string, or ∞.

**Rationale.** The tarball's ten tiers (`english-words.10` … `.95`, confirmed by
listing the archive) are **nested by construction**: tier 10 ⊂ tier 20 ⊂ … ⊂ tier
95. Ten binary columns would feed the model ten perfectly dependent detectors,
wrecking the identifiability check (§5.2 rank, §5.3 profile likelihood) for no
information gain.

---

## D-022 — hunspell is expanded to surface forms with `spylls`

**2026-08-16** · settled

**Rationale.** A `.dic` file is stems plus affix flags, not a word list, so
"hunspell lists X" is ambiguous between *X is a stem* and *X is generated by a
stem and an affix rule* — and the two give very different `record_count`s, which
makes it a live threat to the manifest's reproducibility gate rather than a
detail. No `hunspell` or `aspell` binary is installed and none is needed:
`spylls` (0.1.7, 1.51 MB, pure Python, no dependencies) expands `.dic` + `.aff`.
`MANIFEST.toml` records `expansion = "spylls"` so the choice is in writing rather
than buried in an ingest script.

---

## D-023 — web2 is included as an independent detector

**2026-08-16** · settled

macOS ships `/usr/share/dict/words` → `web2`, Webster's Second International
(1934), public domain, **234,428 entries** under the pinned normalization.

**Rationale.** Its lineage is independent of every other source in the manifest:
NWL/TWL descends from OSPD from Merriam-Webster, hunspell from SCOWL, wordfreq
aggregates over corpora ingested separately. web2 predates all of it. In a design
whose main threat to validity is conditional dependence, a detector with **no
declared edges into the rest of the graph** is unusually valuable — and it is
already on disk. Measured contribution: web2 alone moves **45,280** candidates
out of the all-zero cell that neither WordNet nor Wiktionary reaches.

---

## D-024 — The adjudication budget is ~14.9 hours, not ~9.2

**2026-08-16** · settled (correction)

1,770 presentations — 1,500 calibration (150 per posterior decile, **equal**
allocation), 120 anchors, 150 self-consistency re-presentations — at the measured
**searched** rate of **30.4 s/item**: **≈ 14.9 hours**.

**Rationale.** The rehearsal's headline 20.1 s/item blends searched and unsearched
items (30.4 s against 9.8 s). D-006 makes searching mandatory, so the blended
rate no longer applies and the ~9.2-hour extrapolation understates by roughly six
hours. The always-search rule buys the independence the Rogan–Gladen correction
assumes, which is not optional — but the price belongs in the plan rather than in
Phase 4.

Equal rather than proportional allocation across deciles because the object is a
reliability diagram, which wants comparable precision in every bin rather than an
efficient estimate of the mean. At 150 per bin a Wilson interval is roughly ±8
points at p = 0.5.

---

## D-025 — The form rules lose both length bounds; the EOL is no longer Scrabble-conformant

**2026-08-16** · settled · *authorised by the dataset owner*

The form rule becomes **`^[a-z]+$` with no length bound**. The 2-character minimum
and the 45-character maximum are removed.

**Rationale.** Both bounds were inherited from Scrabble tournament dictionaries,
and both excluded strings that are words of English under D-001's definition.

- **The minimum excluded `a` and `i`.** No Scrabble list can contain them:
  measured, ENABLE, SOWPODS, NWL2023 and CSW21 hold **zero** one-letter entries
  between them. WordNet, web2 and words_alpha each hold all 26, but as glyph
  names. The bound was a game rule wearing the costume of a lexical one.
- **The maximum excluded attested chemistry.**
  `phosphoribosylaminoimidazolesuccinocarboxamide` is 46 characters and carries a
  Wiktionary English entry. Chemical nomenclature is productive and unbounded, so
  any numeric ceiling is arbitrary.

The project's goal is the largest defensible list of English words, not a
Scrabble-legal one. Where the two conflict, the definition wins and the game
convention goes. This is a deliberate, narrow divergence from Scrabble legality
and must be stated on every public surface.

**It admits no garbage.** The four over-length strings on the invalid list are
Welsh, Māori and Fijian place names, excluded by being proper nouns — a semantic
judgement for gate G4, which is what should have been excluding them all along.

**An ingest-time integrity flag replaces the ceiling**, at 100 characters. It
guards against concatenation bugs and is explicitly *not* a form rule. Longest
candidate today: 63 characters. Nothing exceeds 100.

**Consequence for the tripwires, and it is a happy one.** Under the old
`^[a-z]{2,45}$` the WordNet figures were 77,477 / 57,967, while the loose
`isalpha() and isascii()` gave 77,503 / 57,977 — a drift flagged in D-019 as a
defect. Under `^[a-z]+$` **the two filters agree exactly** at 77,503 / 57,977. The
rule change removed the ambiguity rather than adding to it.

---

## D-026 — The candidate frame is augmented by every ingested source

**2026-08-16** · settled

Every source ingested in Phase 1 contributes its form-valid strings to the
candidate frame as well as a detector column. The frame is no longer
inherited-only, which amends D-002 in one respect: D-002 governs *labels*, and
stands; the *frame* is now open.

**Rationale, measured 2026-08-16.** The inherited frame is missing roughly
**248,000 English words** (95% interval 200,000–317,000): 98,032 counted exactly
against seven curated sources, plus ~153,900 extrapolated from a 500-title
Wiktionary sample where 5.00% carried an English section [3.41%, 7.28%].

**Nineteen of the missing appear in all seven curated sources** — `irrespective`,
`southerner`, `guesthouse`, `unverified`, `chihuahua`, `decaffeinate` among them —
verified by direct file search against both the local snapshot and the live
dataset, not inferred from set arithmetic. The identifiable hole is British
Scrabble vocabulary: ENABLE is 99.76% covered, Collins CSW21 only 69.16%.

**Why it could not be deferred.** Capture–recapture estimates what no *source*
caught. It cannot recover what the *frame* never held, because a string that is
not a candidate never receives a probability at all — it is absent, not scored
low. Every downstream quantity is conditional on the frame, so a biased frame
biases all of them in the same direction, invisibly.

**Declared honestly:** words entering by this route carry at least one positive
detection by construction, so the frame is source-dependent. Recorded in
`MANIFEST.toml` as `frame_is_source_augmented`. It marginally *helps* SR2 rather
than hurting it.

---

## D-027 — Single letters are candidates, not automatic entries

**2026-08-16** · settled

D-025 makes single letters form-legal. It does **not** make them valid. All 26
become candidates and are adjudicated on evidence like everything else, with two
exceptions the owner ruled on directly: **`a` and `i` are valid.**

**Rationale.** The obvious lookup does not work, which is worth recording so
nobody repeats it. Wiktionary assigns a **word-level part of speech to 25 of the
26 letters** in English — including `q` as a determiner and `r` as a verb, from
eye-dialect and text-speak entries. The Scrabble lists are silent by construction
(zero one-letter entries). WordNet, web2 and words_alpha list all 26 as glyph
names, which is a *mention* of the character and fails gate G1 by definition.

So no source can settle this, which is precisely the situation the four gates
exist for. Assigning validity by hand here would be the judgement call this
programme exists to eliminate.

**Present state, for the record.** Ten letters sit on the valid list
(a b c d e i n p s v) and eight on the invalid list (f g h j k q r t), on no
evidential basis — an accident of ingest history. Eight are absent entirely
(l m o u w x y z). The correction moves every letter except `a` and `i` to
candidate status and adds the eight missing ones, so all 26 are present and only
two are asserted.

---

## D-028 — Nineteen hyphen-stripped concatenations are attested and must be promoted

**2026-08-16** · settled

Checking the 168 whole hyphenated entries found that **35 of their concatenations
are attested by at least one curated source, and 19 of those are not on the valid
list.** Ten sit on the invalid list and nine are absent from the frame entirely.

| Concatenation | From | Currently | Attested by |
|---|---|---|---|
| `photorealistic` | photo-realistic | absent | SOWPODS, NWL2023, CSW21 |
| `hardshell` | hard-shell | absent | SOWPODS, CSW21, words_alpha |
| `hardnosed` | hard-nosed | absent | SOWPODS, CSW21 |
| `kneejerk` | knee-jerk | absent | SOWPODS, CSW21 |
| `getout` | get-out | invalid | NWL2023, CSW21 |
| `highhanded` | high-handed | invalid | web2, ENABLE, words_alpha |
| `longsuffering` | long-suffering | absent | SOWPODS, words_alpha |
| `heavyhanded` | heavy-handed | invalid | web2, words_alpha |
| `soso` | so-so | invalid | web2, words_alpha |
| `sawtoothed` | saw-toothed | invalid | NWL2023 |
| `gogetting`, `illhumored`, `slowwitted` | (three) | absent | words_alpha |
| `avantgarde`, `bangup`, `hardboiled`, `highhat`, `wellfounded`, `wellread` | (six) | invalid | words_alpha |

**Rationale.** The owner asked whether any hyphen-stripped form might coincidentally
be a real word not already held. The answer is yes, nineteen times. Without the
check, deleting the 188 hyphenated entries would have silently discarded evidence
for nineteen attested words — three of them backed by three independent sources.

Attestation is **evidence, not a verdict** (D-001). These nineteen enter as
candidates carrying their detections; the model rules on them. The remaining 133
concatenations have no attestation and enter as ordinary candidates.

---

## D-029 — Public surfaces change with the data, not before it

**2026-08-16** · settled

`README.md`, the site, the blog, the changelog and the Hugging Face dataset card
are updated **in the same commit sequence that changes the data**, never ahead of
it.

**Rationale.** These surfaces describe the dataset to other people. A README
announcing that one-letter words are accepted, published while the list still
holds none and still carries 190 malformed entries, is simply false — and it is
false in the direction that most damages the project's credibility, since the
whole claim of this work is that its numbers can be checked. Documentation that
runs ahead of the artifact is worse than documentation that lags it.

The governance documents are the exception and are updated immediately: they
describe *intent and method*, they are uncommitted, and their entire job is to be
correct before the work rather than after.

---

## D-030 — Corpus sources provide features over the frame, never frame membership

**2026-08-17** · settled

D-026 makes every ingested source contribute its form-valid strings to the
candidate frame. Phase 1 implementation forced the question it left open: does
that include the corpus sources? **No.** The frame is augmented by the binary
detector sources only — WordNet, Wiktionary-English, web2, the four hunspells,
ENABLE, SOWPODS, NWL2023, CSW21, SCOWL. Google Books and wordfreq contribute
feature columns over whatever frame exists, and nothing to its membership.

**Rationale.** Four reasons, in decreasing order of force.

- **D-026's own wording couples membership to detectorhood** — "contributes its
  form-valid strings to the candidate frame *as well as a detector column*."
  Google Books never gets a detector column: §2.4 measured why it cannot be
  binarised, and wordfreq's membership IS a frequency threshold, which is the
  same prohibition. Sources that contribute no detector contribute no members.
- **The mechanical consequence would gut SR2.** Google Books contains millions
  of form-valid OCR types that no curated source lists. Adding them wholesale
  puts an enormous all-zero-on-every-detector mass into the frame *by
  construction* — the stopping rule would fire not as a measurement but as an
  arithmetic identity, which tells nobody anything.
- **It would triple the sampling-frame contamination §2.4 exists to contain.**
  The candidate set is OCR-derived; so is Google Books. A frame defined as
  "every string Google ever scanned" is the contaminated population at full
  scale, and S5 would be asked to carry the whole load.
- **Population semantics.** The paper describes the frame as "strings asserted
  by the inherited list or by a curated source". That is a population someone
  can reason about. "Strings observed at least 40 times in scanned books" is a
  different and worse one.

**The cost is visible, not hidden:** the SR2 report states how many form-valid
Google Books types the frame declines to include. Words in books that no list
ever caught are exactly what the capture–recapture estimate is *for* — they are
estimated, not enumerated.

---

## D-031 — Case conventions are per-source, pinned by the recorded tripwires

**2026-08-17** · settled

The pinned normalization casefolds. Two sources qualify how they meet it, and
the tripwire numbers recorded in CLAUDE.md §4 already encode both conventions —
this entry writes down what those numbers imply so nobody re-derives it wrong.

- **Wiktionary is case-sensitive by design**: `polish` and `Polish` are
  different pages describing different lemmas. Its ingest therefore accepts
  lowercase titles only, rather than casefolding capitalized titles onto
  lowercase keys — folding would inject every capitalized proper-noun page
  into a *lexicographic detector* as evidence for the common word. The
  recorded title tripwire (4,416,714 under the old rule; 4,416,747 under
  `^[a-z]+$`, the +33 being exactly the 26 letters and 7 long titles) was
  measured under this convention.
- **Flat word lists casefold** (WordNet, web2, ENABLE, SOWPODS, NWL, CSW,
  SCOWL, hunspell): their capitalization is orthographic, not lexical, and the
  recorded tripwires (77,503 WordNet keys, 57,977 ∩ valid, 234,454 web2) were
  measured under casefold.
- **Google Books casefolds and sums**: it is a corpus of occurrences, not
  lemmas. Case variants of one word in one year can share volumes, so summed
  volume_count overcounts for capitalization-heavy words — recorded in the
  manifest as a documented bias on a feature, acceptable where it would not be
  on a count.

**Rationale.** One rule applied blindly would be simpler and wrong twice over:
casefolded Wiktionary titles would hand `london` a dictionary detection, and
lowercase-only word lists would drop every entry NWL prints in capitals — which
is all of them. The conventions follow what each source's case actually means,
and the tripwires freeze them.

---

## D-032 — SR2 is evaluated under reading B; reading A becomes a reported diagnostic

**2026-08-17** · settled · *ruled by the dataset owner on the Phase 1 report*

SR2's operative test: the undifferentiated stratum is the set of frame words
with an all-zero binary detector pattern AND no corpus data of any kind. At
Phase 1 close that stratum holds **845,150 words — 8.63%** of the 9,787,841-word
frame, passing the 50% threshold. Phase 2 proceeds.

**Rationale.** The rule's motivation (§7) is "the majority of the population
shares one posterior." Under S4/S5 the corpus features differentiate within a
binary pattern — two all-zero words with different volume histories receive
different posteriors — so the sharing SR2 forbids does not occur merely because
the binary detectors are silent. Reading A, the tuple-of-detectors reading,
fires at **90.50% by construction**: the curated detectors are near-subsets of
one another, and no amount of curated ingest was going to differentiate an
OCR-era candidate mass. What reading A measures is the limitation of the pure
latent-class specifications S1–S3, not of the evidence layer.

**Reading A's number is still reported in the paper**, as the honest bound for
S1–S3: any specification that sees only the binary pattern hands one posterior
to 8,858,214 words, and that sentence belongs in print next to the model
comparison.

**Recorded with the ruling:**

- The 845,150 no-evidence words are the frame's hardest stratum and the
  population estimate's blind spot — nothing anywhere attests them, so
  capture–recapture extrapolates into them entirely on model structure.
- **The Phase 4 adjudication sample must stratify over this stratum
  explicitly**, not merely by posterior decile: posteriors inside it will
  cluster, and a decile stratification alone could sample it almost entirely
  from one cell.

---

## D-033 — Governance mechanism 1 is implemented, and the drift it would have caught is repaired

**2026-08-18** · settled

PROTOCOL §9 has ranked "every number comes from code… enforced by a check that
re-derives the numbers quoted in markdown and fails on mismatch" as the
highest-leverage governance mechanism since Phase 0. **The check was specified
and never built.** A status review on 2026-08-18 found fifteen documentation
defects in PROTOCOL.md — eleven stale figures and four method statements
superseded by Phase 2 — every one of them exactly the drift the unbuilt
mechanism was designed to catch. An independent verification pass then
re-derived all fifteen claims from the pinned data and the code before
touching anything: **fifteen of fifteen verified; none refuted.**

**The check now exists**: `research/verify_doc_numbers.py`, wired into pytest
as `tests/test_doc_numbers.py`. It re-derives the quoted figures from the
pinned frame, the derived source sets, the correction ledgers and the
regenerable gate reports; requires them verbatim in PROTOCOL.md and CLAUDE.md;
forbids nine superseded figures from reappearing in PROTOCOL.md; and requires
the one deliberately retained historical table (§3.4) to carry its
supersession label. Run before the repair it reported 19 failures; after, it
passes — and it caught a line-wrap defect in the repair itself on the way.

**The repairs.** PROTOCOL.md now states the pinned-revision counts (345,103 /
9,308,896 / 9,653,999, zero form violations), the post-ingest source counts
(77,503 / 4,416,747 / 775,869 / 234,454), the pinned intersection (57,970),
and the frame (9,787,841 = universe + 133,842; the §3.4 table is kept as the
labelled historical motivation with the SR2 measurement beside it).

**Where protocol text and implementation disagreed, the protocol moved to
match the better implementation, not the reverse:**

- §3.2 productivity: potential productivity P = n₁/N is **not computable** —
  the Google Books 2020 floor is 40 on match count AND volume count (both
  minima re-measured at exactly 40 in this verification), so hapaxes do not
  exist in the corpus under any definition. The instrument is realized
  productivity V/N, and the censoring is visible in the productivity table's
  own zero columns.
- §3.2 dispersion: Gries's DP and Juilland's D need per-part counts the
  year-level aggregates cannot supply; the six supported proxies are named
  instead, as proxies.
- §3.2 orthotactics: the model is interpolated, not back-off, because the
  gate is held-out perplexity and a score that is not a probability
  distribution cannot be gated on.
- §3.3 partitions: assignment is by hash range on sha256(seed:word), not by
  ranking sha256(seed:partition:word) — strictly stronger, since one word's
  membership never depends on the rest of the pool — and the overclaim that
  "assignments are committed" is corrected to what is true: the seed, rule
  and counts are committed and the assignments re-derive exactly.

**Not touched, by rule:** research/DECISIONS.md's own historical figures
(append-only; its five 57,977 occurrences are dated records and correct), the
three data files (checksummed identical at both ends), `is_likely_english`,
and the live dataset.

**Branch note, stated rather than buried:** the repair branched off
`research/phase2-features` rather than bare `main`, because the documents
under repair — including D-032's own SR2 row — and the Phase 2 code they must
match live there; branching off main would have repaired a superseded copy.
