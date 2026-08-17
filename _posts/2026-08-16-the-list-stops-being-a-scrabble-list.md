---
title: "The list stops being a Scrabble list — August 16, 2026"
date: 2026-08-16
tags: [update, rules, corrections, breaking-change]
---

# The list stops being a Scrabble list — August 16, 2026

**Update type:** Rule change and correction
**Words removed:** 190 (form-rule violations)
**Candidates added:** 37
**Universe:** 9,654,152 → 9,653,999

Two things changed today, and the first one is a deliberate break with a
convention this project has followed since it started.

## `a` is a word

The English OpenList had inherited two rules from Scrabble tournament
dictionaries: a word must be at least 2 characters, and at most 45. Both have
been removed. **The form rule is now `^[a-z]+$` with no length bound at all.**

The reason is that both bounds excluded words. Not edge cases — words.

At the bottom, the 2-character floor excluded **`a` and `i`**. It is worth
being precise about why no dictionary could talk us out of this: ENABLE,
SOWPODS, NWL2023 and CSW21 hold **zero** one-letter entries *between them*. Not
because lexicographers doubt that `a` is a word, but because one-letter words
are unplayable in Scrabble and tournament lists are built for the game. The rule
was never a claim about English.

At the top, the 45-character ceiling excluded
**`phosphoribosylaminoimidazolesuccinocarboxamide`**, which is 46 characters,
turns up in the purine synthesis pathway, and has its own Wiktionary entry.
Chemical nomenclature is productive — you can always name a longer compound — so
any ceiling is arbitrary. 45 was chosen because
`pneumonoultramicroscopicsilicovolcanoconiosis` happens to be that long.

We checked whether removing the ceiling would let anything unwanted in. It does
not. The over-length strings it had been catching are place names: two Welsh,
one Māori, one Fijian. Those are excluded for being **proper nouns**, which is a
separate rule and the one that should have been doing that work all along. The
length limit was catching them by accident while also blocking real chemistry.

**This means the list is no longer Scrabble-legal, on purpose.** If you were
relying on that, the site now publishes a `scrabble-legal.txt` download that
applies the 2–45 bounds, and you get exactly what you had before. The
substitution only works in that direction, which is why the change went this
way: you can always filter a larger list down, but you cannot recover words a
list never accepted.

## 190 entries that never followed our own rule

Auditing all 9,654,152 entries against the form rule turned up 190 on the valid
list that failed it — 188 hyphenated and 2 accented. `across-the-board`,
`self-evident`, `norteño`. They predate the rule being written down anywhere.

They are now removed, through a ledger, reversibly, like every other move this
project makes.

**One thing nearly went wrong here, and it is the most interesting part of the
day.** The obvious way to remove `hard-nosed` is to delete it. But strip the
hyphen and you get `hardnosed`, which is a word — it is in Collins and in
SOWPODS. So before deleting anything we stripped the hyphen from all 168
compounds and looked every result up in seven independent sources.

**Thirty-five are attested. Nineteen of those were not on the valid list, and
nine were not anywhere in the dataset at all.** `photorealistic`, backed by three
Scrabble dictionaries. `hardshell`, `kneejerk`, `highhanded`, `getout`,
`longsuffering`. A plain deletion would have destroyed the only trace of them.

All 19 have been added — as **candidates, not as valid words**. A dictionary
listing a word is evidence, never a verdict; they go through the same validation
as everything else.

The 20 truncated fragments (`self-`, `two-`, `high-`) cost nothing: 18 of their
20 stems were already valid, and the other two were already candidates. And
`peléan` turned out to be a duplicate of `pelean`, which was already on the list.

## What happened to the letters

All 26 letters are now form-legal, and all 26 are now in the dataset. **Only `a`
and `i` are marked valid.**

The other 24 are candidates, because no source can settle them and we would
rather admit that than guess. The Scrabble lists are silent by construction.
WordNet, Webster's Second and words_alpha list all 26, but as *names for the
characters* — which is a mention of the glyph, not a use of a word. And
Wiktionary assigns a word-level part of speech to **25 of the 26**, including
`q` as a determiner and `r` as a verb, from eye-dialect entries.

So the lookup that looks obvious is unusable, and hand-picking the "real" letters
would be precisely the kind of judgement call this project is working to remove.
They go to adjudication with everything else.

Before today the split was ten letters valid and eight invalid, with `v` blessed
and `q` rejected on no evidential basis whatsoever. That was an accident of
ingest history, and it is now gone.

## The numbers

| | |
| --- | ---: |
| Deleted — truncated hyphen fragments | 20 |
| Deleted — hyphenated compounds | 168 |
| Deleted — accented | 2 |
| Added — attested concatenations | 19 |
| Added — unattested concatenations | 9 |
| Added — single letters | 8 |
| Added — unaccented form (`norteno`) | 1 |
| **Universe before** | **9,654,152** |
| **Universe after** | **9,653,999** |
| Valid words | 345,099 |

Every difference between the before and after files, in both directions, was
checked against the ledger by a separate script that does not trust the one that
made the changes. Twenty-two checks; an unexplained delta of a single word would
have failed the run. Both lists now satisfy the form rule with zero exceptions
for the first time.

## Why this took a rule change rather than a cleanup

The honest answer is that the audit was looking for something else. It was
checking whether the candidate pool contained anything malformed — and the
answer was reassuring, 12 bad entries in 9.3 million.

But the same scan showed the valid list rejecting `a`, and that is not a defect
in the data. It is a defect in the rule. The list is meant to be the largest
defensible list of English words; where that goal and a game convention
disagree, the goal wins.

Full reasoning, with every decision dated and argued, is in
`research/DECISIONS.md` — entries D-025 through D-029.
