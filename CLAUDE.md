# CLAUDE.md

Loaded automatically every session. Read it before touching anything.

The full method is in [`PROTOCOL.md`](PROTOCOL.md). This file carries only the
rules that must never be rediscovered.

---

## 1. Never write to the three data files

```
merged_valid_words.txt
merged_invalid_words.txt
merged_valid_dict.json
```

Wherever they appear — repo, `.cache/hf/`, `output/`, a working copy, Hugging
Face. **No word is moved by a session. Not one.**

Words move only through a correction ledger in `corrections/`, or through the
nightly pipeline, which is the only automated process permitted to promote.
Phases 0–4 of the measurement programme move nothing at all; the live list, the
site and the nightly pipeline stay untouched until Phase 5.

**Checksum ritual — run at the start and the end of every session, and assert
they match:**

```bash
shasum -a 256 .cache/hf/merged_valid_words.txt .cache/hf/merged_invalid_words.txt .cache/hf/merged_valid_dict.json
```

Baseline for the 2026-08-14 local snapshot:

| File | SHA-256 |
|---|---|
| `merged_valid_words.txt` | `cd1cbff0004425c243c61a06f327fe612684ece1b21567a3ce31c41da7b5fc7e` |
| `merged_invalid_words.txt` | `d640cd2e3a17c03db3438149dd593a8343f153f5146ebb6234d4662b1bc0423f` |
| `merged_valid_dict.json` | `68a0c5d1512a49f85f7f789ede2201932657fae189f9558c2bfa859a137b630f` |

---

## 2. The operational definition

> **A string is a word of English if and only if it has attested, conventional,
> independent use in English text by multiple unrelated authors, and satisfies
> the form rules below.**

Usage-based, deliberately. Under a lexicographic definition dictionaries *are*
the ground truth, the latent-variable model collapses into "ask Merriam-Webster",
and the programme walks back into the wall that stopped the last one.

**Dictionary presence is strong evidence and never definitional.** A string
absent from every dictionary can clear the bar; a string listed in one can fail
it.

**The form rule, as of 2026-08-16, is `^[a-z]+$` with no length bound.** That is
all of it. The owner removed the 2-character minimum and the 45-character maximum
deliberately (D-025), because both were Scrabble conventions that excluded real
English: `a` and `i` at one end, 46-character attested chemistry at the other.
**The EOL is therefore no longer Scrabble-conformant, narrowly and on purpose.**

Two things follow that a session must not undo:

- **`scripts/word_validator.py` still encodes the old 2–45 bounds** until the
  Phase-0.5 correction lands. Where code and protocol disagree, the protocol is
  the intent and the code is the defect.
- **A >100-character ingest flag replaces the ceiling.** It is a data-integrity
  check against concatenation bugs, not a form rule. Nothing in the universe
  currently exceeds 100; the longest is 63.

**The "no proper nouns" rule is not implemented at all** —
`ProperNounDetector.is_likely_proper_noun` returns `False` for every lowercase
string, so lowercase surnames, places and transliterations pass untouched
(`karpiak`, `chetiyagiri`, `benello` are all candidates). Adjudication gate G4
carries that weight. Do not claim a rule the code does not enforce.

---

## 3. `candidate_source` is a discovery log and is never evidence

It records where a candidate was first **seen**, not which sources **contain**
it. It credits WordNet for 2,127 words; the real intersection is **57,977** — a
27× undercount. Any evidence model built on it measures the wrong quantity.

The same goes for the `source` and `confidence` fields in
`merged_valid_dict.json`. **The current dataset contributes exactly one thing:
the 9,654,152 candidate strings.** Every label, attribution and score is
discarded and re-derived from pinned primary sources.

---

## 4. Tripwire counts — with the normalization that produces them

**A count without its filter is not a tripwire.** These move if the filter moves.

Under the pinned normalization — verbatim, and identical in `PROTOCOL.md` §2.5
and `sources/MANIFEST.toml`:

> `NFC; casefold; accept iff ^[a-z]+$`

**Tripwires are pinned to HF revision `c1139698` (2026-08-17)** — the revision
that published the D-025 correction, and the revision Phase 1 reads. The
nightly moves the valid/invalid *split* daily; the universe and the source
counts do not move.

| Quantity | Count |
|---|---:|
| valid list at the pin | 345,103 |
| invalid list at the pin | 9,308,896 |
| **universe (zero form violations)** | **9,653,999** |
| WordNet keys | 77,503 |
| valid ∩ WordNet at the pin | 57,970 |
| Wiktionary lowercase titles (all languages) | 4,416,747 |
| Wiktionary titles with an `== English ==` section | 775,869 |
| web2 keys | 234,454 |

**Every superseded figure is explained, not merely replaced.** 57,977 → 57,970
is −8 demoted letters (D-027) +1 `mavik` (nightly promotion, in WordNet).
234,428 → 234,454 and 4,416,714 → 4,416,747 are exactly the 1-character and
>45-character keys D-025 legalised (+26/+26+7). 77,477 → 77,503 likewise. The
old 9,654,152 / 9,653,962 / “190 outstanding violations” state predates the
published correction; both lists now satisfy the form rule with zero
exceptions, so the raw-lines-versus-form-valid distinction is gone.

If a measurement disagrees with these, **check the filter and the revision
before concluding the data changed** — and if the data did change, explain the
delta to the digit before accepting it, the way the entries above do.

---

## 5. A stale local snapshot is expected

The nightly `daily_update.yml` promotes ~1,000 words per night from the invalid
list using Merriam-Webster. **The valid/invalid split moves every single day.**

So `.cache/hf/` being behind live Hugging Face is normal and is not evidence of
tampering. As of 2026-08-16 the local snapshot is two nightly runs behind.

Consequences that matter:

- The candidate universe is **frozen at a pinned HF revision** in
  `sources/MANIFEST.toml`, never at "the current dataset".
- The current valid list is a **held-out test set, never a fitting target** — and
  it drifts, under an MW-based process, which is exactly the process being
  replaced. Compare against the pinned revision and report its date.

---

## 6. Every number comes from code

No figure appears in any document unless a committed script produced it and can
regenerate it. If you cannot point at the command, do not write the number.

Sampled quantities always carry intervals. **A sampled figure is never reported
as a count.**

Sampling is by `sha256(seed:stratum:word)` ranking, never a library RNG —
recomputable in any language and immune to stdlib changes.

---

## 7. Decisions are appended, not re-litigated

`research/DECISIONS.md` is **append-only**. Every methodological choice is dated
and carries its rationale. If a decision looks wrong, add an entry superseding it
and say why; do not edit or delete the original.

Decisions already settled and **not open for re-argument**: the usage-based
definition; the candidate-set-only inheritance; the current valid list as a
held-out test set; human adjudication as calibration rather than verdict;
searching never skipped; LLM-as-judge as a parallel arm and never the reference
standard; pre-registration after the Phase 3 pilot; no paid APIs.

---

## 8. Standing constraint

**No word is ever permanently invalid.** Under this method that falls out for
free: everything carries a probability and nothing carries a life sentence.
