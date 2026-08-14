# Corrections

Every word this project moves between the valid and the invalid list is recorded
here first. The ledger is the source of truth; the word lists are regenerated
from it. A verdict can therefore be revisited without re-running anything, and
nothing moves without a recorded reason and a source you can go and check.

Until August 2026 the rule on this dataset was that no word is ever added,
removed or altered — documentation and infrastructure only. That was reversed
deliberately by the dataset's owner, not drifted away from. Promotion from the
invalid list to the valid list was always the nightly pipeline's job; what is
new is the ability to move a word the other way. Nothing has yet been moved that
way, and nothing will be without evidence recorded here.

## Ledger format

| Column | Meaning |
| --- | --- |
| `word` | the word |
| `stage` | which stage of the correction decided it |
| `verdict` | `valid` or `invalid` |
| `action` | what was done — currently only `remove_from_invalid_list` |
| `method` | how it was decided (see below) |
| `source` | the authority that ruled |
| `confidence` | `high`, `medium`, `low` |
| `evidence` | what that source actually left behind in the record |
| `part_of_speech` | as recorded by the source |
| `decided_date` | when |

`method` is the important column. `stored_api_ruling` means a dictionary API had
already ruled on the word and the ruling was sitting in the dataset. Any verdict
that ever comes from model judgement rather than a source will say so, so it can
be filtered or revisited later.

## Stage 1 — 150 dual-listed words, 13 August 2026

150 words were in `merged_valid_words.txt` **and** in the 9.2-million-entry
invalid list at the same time. A word must be one or the other.

None of them needed adjudicating. Every one already carried a dictionary ruling
inside its own record in `merged_valid_dict.json`:

| | |
| --- | ---: |
| Ruled by Free Dictionary | 86 |
| Ruled by Merriam-Webster | 63 |
| Ruled by Merriam-Webster Medical | 1 |
| Carrying the full raw API response | 139 |
| Carrying a definition | 149 |
| Carrying a part of speech | 150 |
| Passing `word_validator`'s Scrabble rules | 150 |
| Flagged by Merriam-Webster as an abbreviation | 0 |

They are words like `mpox`, `sertraline`, `capicola`, `arancini`, `hashtag`,
`unfollow`, `doomscrolling` and `chupacabra` — real, recent, correctly promoted.
What went wrong is that they were added to the valid list without being removed
from the invalid one.

So all 150 were cleared as valid and removed from the invalid list. **None was
demoted, and the valid list was not touched.** The stage cost no dictionary API
calls at all, because the evidence was already in the file.

| | Before | After |
| --- | ---: | ---: |
| `merged_valid_words.txt` | 378,891 | 378,891 |
| `merged_invalid_words.txt` | 9,275,411 | 9,275,261 |
| words in both lists | 150 | **0** |

Separately, 201 entries carried `"status": "WordStatus.VALID"` — a Python enum
stringified by a writer that has since been replaced. Those were normalised to
`"valid"`. A line-by-line comparison against the pre-change file found exactly
201 differing lines, all of that one shape, and nothing else.

The build now asserts that no word is in both lists, as an exact zero rather
than a range. If it ever fails, the promotion path in
`scripts/validate_invalid_list.py` has regressed, and widening the bound is the
wrong fix.

### Spot-check

The verdicts rest on rulings recorded in December 2025 – May 2026, so a sample
was re-checked live on 13 August 2026 against the Free Dictionary API — the same
source that ruled on 86 of them, and one that costs no Merriam-Webster quota.

Five of the most obscure Free-Dictionary-sourced words all still return an entry:

| Word | Live result |
| --- | --- |
| `bockety` | adjective — unsteady, wobbly, rickety |
| `cheeselog` | noun — a woodlouse |
| `deurmekaar` | adjective — mixed up, heterogeneous |
| `baggywrinkle` | noun — a rope pad attached to a shroud |
| `skedonk` | noun — an old, battered motor car |

The 63 Merriam-Webster-sourced words could not be independently corroborated
this way: Free Dictionary has none of them, which is why MW ruled on them in the
first place. Their evidence is the stored MW response, which carries the
collegiate source and entry UUID. That is worth knowing when reading the
`high` confidence on those rows — it is one source, recorded, not two agreeing.

### Reproducing it

    python scripts/build_correction_ledger.py --data-dir .cache/hf --out corrections
    python scripts/apply_correction_ledger.py --data-dir .cache/hf \
        --ledger corrections/ledger_stage1.csv --dry-run

The applier refuses any action it does not recognise, and refuses to remove a
word from the invalid list unless that word is in the valid list — that would be
deleting a word rather than correcting one. It is idempotent, so re-running it
against already-corrected data changes nothing.

The state immediately before this change is preserved in two places: the
`stage1-backup-2026-08-13` branch of the private `eol-archive` repository, and
`~/Documents/english-openlist-prune-mirror/stage1-backup-2026-08-13`. Both were
verified to decompress byte-identical before anything was written. Hugging Face
keeps no history to fall back on.

## Not yet decided

Two further defects have been measured but **nothing has been moved for either**:

- **20,052 entries carry `"status": "invalid"` while sitting in the valid list.**
  All of them were marked invalid by a single LLM pass (Google Gemini 3 Flash
  Preview, December 2025) which also passed 117,653 other words. The pipeline's
  own deterministic checks passed 97.8% of them, and `abacavir` — attested in
  COCA, Google Ngrams, Wikipedia and Wiktionary — is among them. It is a second
  opinion of unmeasured quality. Measuring it is the next stage.
- **64,837 synthetic words carry no attestation of any kind** — no corpus source,
  no validation record — while marked `validated: true` and noted as "awaiting
  validation". 95.9% are derived forms of stems already in the list, and 16,478
  of them are comparatives and superlatives on adjectives that cannot take them.
