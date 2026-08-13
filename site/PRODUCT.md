# Product

## Register

product

## Users

Two people arrive here, and they want opposite things.

The **developer** has a game, a puzzle, a spell-checker or a model and needs a
word list. They want to know what is in this one, whether they can trust it, and
how to get it into their project. Their session is ninety seconds long and ends
with something copied to a clipboard. If they leave without a working line of
code, the page failed.

The **curious reader** wants to look at 378,891 words. They came from a link, or
from Ars Magna, and they will type their own name into the box. Their session is
minutes long and ends with them having learned something about the shape of
English — or about the shape of this particular dataset, which is not the same
thing.

Both are served by the same fact: the whole list is in the browser.

## Product Purpose

Make English OpenList legible.

The dataset is a 4.4 MB word list, a 291 MB record of where every word came
from, and a 12.2 GB record of everything rejected. None of that is browsable,
and the metadata is the part nobody sees. This site is the reading surface: search
and filter the list, look at any word's provenance, see the distributions, and
leave with the code to use it yourself.

Two things make it different from a dataset card:

1. **The data is here, not described.** 378,891 words cross the wire in 666 KB
   and every query runs locally. There is no API to be down and no request that
   leaves the browser.
2. **It says what the data actually is.** 17% of these words were constructed
   algorithmically. 20,052 carry a record saying they are invalid. 150 are on
   both the valid and the invalid list. A site that hid that would be easier to
   admire and worse to build on.

## Brand Personality

Inherited from Ars Magna, and deliberately not distinguished from it: precise,
scholarly, quietly playful. The two sites share an author and a dictionary, and
a visitor arriving from one should recognise the other.

Copy is exact and unfussy. No exclamation marks, no encouragement, no mascot.
The wit lives in the substance — the interesting thing about this dataset is
that it contains `abacteremicer`, and saying so plainly is funnier than a joke
about it.

Voice test: the empty state reads *"Nothing matches 'qxz'"*, not *"No results
found — try a different search!"*

## Anti-references

- **Warm cream / parchment / sand backgrounds.** The saturated default of the
  moment, and a poor surface for reading tens of thousands of words.
- **Dataset landing pages that are all badge and no data.** Download counts,
  logos, a "Get started" button, and no way to see a single row.
- **Dashboard chrome for its own sake.** A stat tile that restates a number
  already in the sentence above it is decoration.
- **Word-game cuteness.** No tile graphics, no confetti, no Scrabble-rack
  skeuomorphism.

## Design Principles

1. **The words are the interface.** Type carries the visual weight; chrome is
   hairlines and space.
2. **State the number.** The exact count appears before any result does.
3. **Never imply completeness you don't have.** Every cap, gap and contradiction
   in the data is said out loud, in the interface, next to the thing it affects.
4. **Every snippet has been run.** Code on this site ships with the output it
   actually produced. A snippet nobody executed is a guess with syntax
   highlighting.
5. **Filters over pagination.** With 378,891 rows the answer to "too many" is a
   better query.

## Where this departs from Ars Magna

Ars Magna's PRODUCT.md forbids charts outright — "no stat tiles, no cards, no
sparklines" — because it has exactly one number worth showing, the result count.
This site is about the shape of a dataset, so distributions are the substance
rather than chrome, and it draws them.

The anti-references still hold. Charts here are ink and one accent, hairline
grids, no gradients, no rounded bar caps, no chart library, and no CDN. The
intake scale runs from the accent through to faint grey rather than using four
hues, because rank is the information and hue would only decorate it.

## Accessibility & Inclusion

Best-effort baseline rather than a formal audit target: 4.5:1 contrast on body
text, visible focus rings on every interactive element, full keyboard operation
of the controls and the result list, and `prefers-reduced-motion` honoured. The
result count updates a polite live region so it is not silent to screen readers.
Charts carry the figures in text as well as in the drawing.
