"""
The fast sources: everything that ingests in minutes rather than hours.

Each function fetches its pinned artifact, derives the source's normalized key
set, and writes it beside a meta JSON via `write_derived`. The two long-running
sources — the Wiktionary article dump and the Google Books shards — live in
their own modules.

Case conventions, because they are where the counts hide (and the tripwires in
CLAUDE.md §4 encode them):

* Word lists and lexica distributed as flat files (WordNet, web2, ENABLE,
  SOWPODS, NWL, CSW, SCOWL, hunspell) are casefolded. Their capitalization is
  orthographic convention, and the recorded tripwires (77,503 WordNet lemmas,
  57,977 ∩ valid) were measured under casefold.
* Wiktionary is case-SENSITIVE by design — `polish` and `Polish` are different
  lemmas with different pages — so its ingest accepts lowercase titles only.
  That convention lives in the wiktionary modules and in the manifest, not here.
"""

from __future__ import annotations

import io
import re
import tarfile

from . import common
from .common import RAW_DIR, download, normalize, write_derived

URLS = {
    "enable1": "https://raw.githubusercontent.com/dolph/dictionary/master/enable1.txt",
    "sowpods_legacy": "https://raw.githubusercontent.com/jesstess/Scrabble/master/scrabble/sowpods.txt",
    "nwl2023": "https://raw.githubusercontent.com/scrabblewords/scrabblewords/main/words/North-American/NWL2023.txt",
    "csw21": "https://raw.githubusercontent.com/scrabblewords/scrabblewords/main/words/British/CSW21.txt",
    "scowl": "https://downloads.sourceforge.net/wordlist/scowl-2020.12.07.tar.gz",
    "hunspell_dic": "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/en/{loc}.dic",
    "hunspell_aff": "https://raw.githubusercontent.com/LibreOffice/dictionaries/master/en/{loc}.aff",
}

SCOWL_CATEGORIES = ("english", "american", "british", "british_z",
                    "canadian", "australian")
SCOWL_SIZES = (10, 20, 35, 40, 50, 55, 60, 70, 80, 95)


def ingest_wordnet() -> dict:
    """Installed via nltk; the artifact is the wordnet.zip already on disk."""
    from nltk.corpus import wordnet as wn
    from pathlib import Path
    words = set()
    for syn in wn.all_synsets():
        for lemma in syn.lemmas():
            key = normalize(lemma.name())
            if key:
                words.add(key)
    artifact = Path.home() / "nltk_data" / "corpora" / "wordnet.zip"
    sha = common.sha256_file(artifact) if artifact.exists() else None
    return write_derived("wordnet", words, artifact_sha256=sha,
                         url="nltk corpora/wordnet (installed)",
                         extra={"wordnet_version": wn.get_version()})


def ingest_web2() -> dict:
    """Webster's Second (1934), shipped with macOS. Lineage independent of
    every modern source in the manifest, which is its whole value."""
    from pathlib import Path
    path = Path("/usr/share/dict/words")
    words = set()
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            key = normalize(line.strip())
            if key:
                words.add(key)
    return write_derived("web2", words, artifact_sha256=common.sha256_file(path),
                         url="file:///usr/share/dict/words")


def ingest_plain_list(source_id: str, *, first_token: bool = False) -> dict:
    """ENABLE, SOWPODS, NWL2023, CSW21 — flat lists, one entry per line.

    NWL and CSW carry a definition after the word, so `first_token` splits it
    off. Both are proprietary (redistributable = false in the manifest): the
    derived files stay in .cache/, which is gitignored, and never ship."""
    url = URLS[source_id]
    dest = RAW_DIR / f"{source_id}{'.txt' if not url.endswith('.gz') else '.gz'}"
    sha = download(url, dest)
    words = set()
    with open(dest, encoding="utf-8", errors="ignore") as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            key = normalize(parts[0] if first_token else line.strip())
            if key:
                words.add(key)
    return write_derived(source_id, words, artifact_sha256=sha, url=url)


def ingest_scowl() -> dict:
    """
    SCOWL's ten size tiers, as ONE ordinal covariate (D-021).

    The tiers are nested by construction — the list at size S is the union of
    every marginal file with size ≤ S — so the ordinal value for a word is the
    size of the smallest tier containing it. Ten binary columns would hand the
    model ten perfectly dependent detectors and wreck the identifiability check
    for no information gain.

    Included: the six English-variant `*-words.N` files. Excluded: abbreviations,
    contractions, proper names and upper — those fail the form rule or the
    definition by construction.

    The derived .txt is the membership set (any tier); the tier map itself is
    written as scowl_tiers.tsv beside it.
    """
    url = URLS["scowl"]
    dest = RAW_DIR / "scowl-2020.12.07.tar.gz"
    sha = download(url, dest)
    tier: dict[str, int] = {}
    with tarfile.open(dest, "r:gz") as tar:
        for member in tar.getmembers():
            m = re.match(
                r"scowl-2020\.12\.07/final/(%s)-words\.(\d+)$"
                % "|".join(SCOWL_CATEGORIES), member.name)
            if not m:
                continue
            size = int(m.group(2))
            if size not in SCOWL_SIZES:
                continue
            fh = tar.extractfile(member)
            assert fh is not None
            # SCOWL ships ISO-8859-1; accented entries fail the form rule anyway.
            for line in io.TextIOWrapper(fh, encoding="latin-1"):
                key = normalize(line.strip())
                if key and size < tier.get(key, 999):
                    tier[key] = size
    words = set(tier)
    meta = write_derived("scowl", words, artifact_sha256=sha, url=url,
                         extra={"tier_values": sorted(set(tier.values()))})
    with open(common.DERIVED_DIR / "scowl_tiers.tsv", "w", encoding="utf-8") as f:
        for w in sorted(tier):
            f.write(f"{w}\t{tier[w]}\n")
    meta["tiers_sha256"] = common.sha256_file(common.DERIVED_DIR / "scowl_tiers.tsv")
    return meta


# ---------------------------------------------------------------------------
# hunspell — .dic + .aff expanded to surface forms with spylls (D-022)
# ---------------------------------------------------------------------------

def _expand_hunspell(dic_path, aff_path) -> set[str]:
    """
    Unmunch: stems × affix rules → surface forms.

    A .dic file is stems plus flags, not a word list, so "hunspell lists X" is
    ambiguous until this step. spylls (pure Python, no binary) parses the pair;
    this walks each stem's flags, applies matching suffixes and prefixes, and
    takes the prefix×suffix cross-product where both rules allow it. One level
    of suffix continuation is followed — the en_* dictionaries use it barely at
    all, and deeper chains produce forms hunspell itself would not accept.
    """
    from spylls.hunspell import Dictionary
    d = Dictionary.from_files(str(dic_path.with_suffix("")))
    aff = d.aff

    def rule_applies(rule, stem: str) -> bool:
        regex = getattr(rule, "cond_regexp", None)
        if regex is None:
            return True
        return bool(regex.search(stem))

    def apply_suffix(rule, stem: str) -> str | None:
        if not rule_applies(rule, stem):
            return None
        base = stem[: len(stem) - len(rule.strip)] if rule.strip else stem
        return base + rule.add

    def apply_prefix(rule, stem: str) -> str | None:
        if not rule_applies(rule, stem):
            return None
        base = stem[len(rule.strip):] if rule.strip else stem
        return rule.add + base

    forms: set[str] = set()
    for word in d.dic.words:
        stem = word.stem
        flags = word.flags or set()
        forms.add(stem)
        suffixed: list[tuple[str, object]] = []
        for flag in flags:
            for sfx in aff.SFX.get(flag, []):
                out = apply_suffix(sfx, stem)
                if out is None:
                    continue
                forms.add(out)
                suffixed.append((out, sfx))
                # one level of continuation (e.g. plural of a derived form)
                for cont_flag in getattr(sfx, "flags", ()) or ():
                    for sfx2 in aff.SFX.get(cont_flag, []):
                        out2 = apply_suffix(sfx2, out)
                        if out2 is not None:
                            forms.add(out2)
        for flag in flags:
            for pfx in aff.PFX.get(flag, []):
                out = apply_prefix(pfx, stem)
                if out is None:
                    continue
                forms.add(out)
                if getattr(pfx, "crossproduct", False):
                    for suf_form, sfx in suffixed:
                        if getattr(sfx, "crossproduct", False):
                            both = apply_prefix(pfx, suf_form)
                            if both is not None:
                                forms.add(both)
    return forms


def ingest_hunspell(locale: str) -> dict:
    """One of en_US, en_GB, en_CA, en_AU."""
    dic_url = URLS["hunspell_dic"].format(loc=locale)
    aff_url = URLS["hunspell_aff"].format(loc=locale)
    dic_path = RAW_DIR / f"{locale}.dic"
    aff_path = RAW_DIR / f"{locale}.aff"
    dic_sha = download(dic_url, dic_path)
    aff_sha = download(aff_url, aff_path)
    raw_forms = _expand_hunspell(dic_path, aff_path)
    words = set()
    for form in raw_forms:
        key = normalize(form)
        if key:
            words.add(key)
    return write_derived(f"hunspell_{locale}", words,
                         artifact_sha256=dic_sha, url=dic_url,
                         extra={"aff_sha256": aff_sha, "aff_url": aff_url,
                                "expansion": "spylls",
                                "raw_form_count": len(raw_forms)})


def ingest_wordfreq() -> dict:
    """
    wordfreq's English vocabulary, with each word's zipf frequency.

    A corpus source: presence in wordfreq's list IS a frequency threshold, so
    it never becomes a binary detector column (PROTOCOL.md §3.1). The zipf
    value is the feature; the derived .txt exists for bookkeeping and the
    frame question, not as a detector.
    """
    import importlib.metadata
    import wordfreq
    words: dict[str, float] = {}
    for token in wordfreq.iter_wordlist("en", wordlist="best"):
        key = normalize(token)
        if key and key not in words:
            words[key] = wordfreq.zipf_frequency(key, "en")
    meta = write_derived("wordfreq", set(words), artifact_sha256=None,
                         url="pypi:wordfreq",
                         extra={"package_version": importlib.metadata.version("wordfreq")})
    with open(common.DERIVED_DIR / "wordfreq_zipf.tsv", "w", encoding="utf-8") as f:
        for w in sorted(words):
            f.write(f"{w}\t{words[w]}\n")
    meta["zipf_sha256"] = common.sha256_file(common.DERIVED_DIR / "wordfreq_zipf.tsv")
    return meta


def ingest_wiktionary_titles() -> dict:
    """
    The 27.8 MB all-titles index — a SCREEN, not a verdict (manifest notes).

    Case-sensitive source: only titles that are already lowercase count, since
    `London` and `london` are different pages and different lemmas. `agiler`
    is the standing reminder that a title hit means *some* language uses the
    spelling; English is confirmed by the article-dump ingest, which produces
    the separate `wiktionary_english` source that actually enters the model.
    """
    import unicodedata
    path = common.REPO / ".cache" / "wiktionary" / "all-titles.gz"
    words = set()
    with common.open_maybe_gzip(path, errors="ignore") as f:
        next(f, None)  # header line
        for line in f:
            t = line.rstrip("\n")
            if "\t" in t:
                t = t.split("\t")[-1]
            t = unicodedata.normalize("NFC", t)
            if common.FORM_RULE.fullmatch(t):   # lowercase-only, no casefold
                words.add(t)
    return write_derived("wiktionary_titles", words,
                         artifact_sha256=common.sha256_file(path),
                         url=("https://dumps.wikimedia.org/enwiktionary/latest/"
                              "enwiktionary-latest-all-titles-in-ns0.gz"))
