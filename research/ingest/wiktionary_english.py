"""
Wiktionary with the `== English ==` confirmation — the source that enters the
model.

The title index says *some* language uses a spelling. This streams the full
article dump and keeps only pages that both have a lowercase form-valid title
AND carry an English language section. That confirmation is necessary, not
sufficient: `agiler` — long this project's canonical German-only example — now
carries a community-added `English: comparative of agile` section, and the
ingest reports it faithfully. Wiktionary is a noisy detector; weighing it is
the model's job, not the parser's. Wiktionary titles are
case-sensitive lemmas — `polish` and `Polish` are different pages — so the
lowercase-title convention here is the source's own semantics, declared in the
manifest, not a loosening of the pinned normalization.

Disk discipline: the 1.6 GB dump is downloaded, streamed once, and deleted.
The manifest re-fetches it by pinned URL; nothing large is hoarded.

Run:  python -m research.ingest.wiktionary_english
"""

from __future__ import annotations

import bz2
import re
import sys
import time
import unicodedata

from .common import FORM_RULE, RAW_DIR, download, sha256_file, write_derived

URL = ("https://dumps.wikimedia.org/enwiktionary/latest/"
       "enwiktionary-latest-pages-articles.xml.bz2")

TITLE = re.compile(r"<title>([^<]*)</title>")
# A level-2 heading whose name is English, either at line start or immediately
# after the `<text ...>` element's closing `>` — pages whose wikitext BEGINS
# with the English section (most English-first pages) put the heading on the
# same line as the XML tag, and a line-start-only match silently loses them.
# That miss was caught live: 7M pages in, the count was a third of what the
# title index implies, and every missing page started `<text ...>==English==`.
ENGLISH = re.compile(r"(?:^|>)==\s*English\s*==\s*$")


def main() -> int:
    dest = RAW_DIR / "enwiktionary-latest-pages-articles.xml.bz2"
    print(f"[wikt-en] downloading {URL}", flush=True)
    sha = download(URL, dest)
    print(f"[wikt-en] artifact sha256 {sha}", flush=True)

    words: set[str] = set()
    pages = 0
    candidate_title: str | None = None
    t0 = time.time()

    with bz2.open(dest, "rt", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "<title>" in line:
                pages += 1
                if pages % 1_000_000 == 0:
                    print(f"[wikt-en] {pages:,} pages, {len(words):,} English "
                          f"a-z entries, {time.time()-t0:,.0f}s", flush=True)
                m = TITLE.search(line)
                candidate_title = None
                if m:
                    t = unicodedata.normalize("NFC", m.group(1))
                    # lowercase-only by convention; casefold would fold proper
                    # nouns' pages onto common-word keys (London -> london).
                    if FORM_RULE.fullmatch(t) and t not in words:
                        candidate_title = t
            elif candidate_title is not None and "English" in line and "==" in line:
                if ENGLISH.search(line.rstrip("\n")):
                    words.add(candidate_title)
                    candidate_title = None

    meta = write_derived("wiktionary_english", words, artifact_sha256=sha, url=URL,
                         extra={"pages_scanned": pages})
    print(f"[wikt-en] DONE: {meta['record_count']:,} entries from {pages:,} pages "
          f"in {time.time()-t0:,.0f}s", flush=True)

    dest.unlink()  # 1.6 GB; the manifest makes it re-fetchable
    print("[wikt-en] dump deleted", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
