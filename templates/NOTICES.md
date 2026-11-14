# NOTICES: the English OpenList

The maintainer's own contribution to this dataset is under the MIT License. The
dataset does not relicense what it took from others. This file carries the
notices, licenses, and credits of the sources it names, in the sources' own
words where their terms require the text itself.

## What each record takes from the sources

`attested_by` in `merged_valid_dict.json` names the openly licensed sources whose
own files list a word: `wiktionary`, `wordnet`, `scowl`, `libreoffice`, `enable`,
and `wordfreq`. It records that a source lists the word; no source's text is
copied into the records. The pass that fills it is `scripts/open_attestation.py`
in https://github.com/ryanjosephkamp/english-openlist, run against these copies:

| Key | Source | Copy | License |
|---|---|---|---|
| `wiktionary` | The English Wiktionary | pages-articles dump of August 1, 2026: page titles with an English section | CC BY-SA 4.0 and GFDL |
| `wordnet` | WordNet 3.0, Princeton University | as nltk distributes it | WordNet 3.0 license |
| `scowl` | SCOWL, Kevin Atkinson | 2020.12.07, all sizes and spelling varieties | SCOWL's notice |
| `libreoffice` | The LibreOffice English dictionaries | en_US, en_CA, en_AU, and en_GB at commit `f2ff9905` | SCOWL's notice; en_GB under the LGPL |
| `enable` | ENABLE, Alan Beale and M. Cooper | `enable1.txt`, 172,823 words | Public domain |
| `wordfreq` | wordfreq, Robyn Speer | 3.1.1, English | CC BY-SA 4.0 (data) |

## The English Wiktionary

`attested_by` names `wiktionary` when the word is the title of a page with an
English section in the English Wiktionary's pages-articles dump of August 1, 2026
(https://dumps.wikimedia.org/enwiktionary/). The text of Wiktionary is written by
its contributors and is available under the Creative Commons Attribution-ShareAlike
License (https://creativecommons.org/licenses/by-sa/4.0/) and the GNU Free
Documentation License, under the Wikimedia Foundation's Terms of Use
(https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use). Each page's history
lists its authors (https://en.wiktionary.org/wiki/Special:History).

`source: "free-dictionary"` records that the Free Dictionary API
(https://dictionaryapi.dev/), which draws its entries from the English Wiktionary,
returned an entry for the word. Its responses carry the license CC BY-SA 3.0. The
nightly run uses it to promote words from the candidate list; no text from it is
kept in the records.

## WordNet 3.0 (Princeton University)

`attested_by` names `wordnet` when the word is a WordNet 3.0 lemma, or a form that
WordNet's own morphology (`morphy`, with its exception lists) maps to a lemma, as
nltk distributes WordNet. Its license, verbatim:

    WordNet Release 3.0

    This software and database is being provided to you, the LICENSEE, by
    Princeton University under the following license.  By obtaining, using
    and/or copying this software and database, you agree that you have
    read, understood, and will comply with these terms and conditions.:

    Permission to use, copy, modify and distribute this software and
    database and its documentation for any purpose and without fee or
    royalty is hereby granted, provided that you agree to comply with
    the following copyright notice and statements, including the disclaimer,
    and that the same appear on ALL copies of the software, database and
    documentation, including modifications that you make for internal
    use or for distribution.

    WordNet 3.0 Copyright 2006 by Princeton University.  All rights reserved.

    THIS SOFTWARE AND DATABASE IS PROVIDED "AS IS" AND PRINCETON
    UNIVERSITY MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
    IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PRINCETON
    UNIVERSITY MAKES NO REPRESENTATIONS OR WARRANTIES OF MERCHANT-
    ABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE USE
    OF THE LICENSED SOFTWARE, DATABASE OR DOCUMENTATION WILL NOT
    INFRINGE ANY THIRD PARTY PATENTS, COPYRIGHTS, TRADEMARKS OR
    OTHER RIGHTS.

    The name of Princeton University or Princeton may not be used in
    advertising or publicity pertaining to distribution of the software
    and/or database.  Title to copyright in this software, database and
    any associated documentation shall at all times remain with
    Princeton University and LICENSEE agrees to preserve same.

## SCOWL 2020.12.07 (Kevin Atkinson), and the en_US, en_CA, and en_AU dictionaries

`attested_by` names `scowl` when the word is in SCOWL 2020.12.07, at any size and
in any spelling variety, and `libreoffice` when the en_US, en_CA, en_AU, or en_GB
LibreOffice dictionary produces it. The READMEs of the en_US, en_CA, and en_AU
dictionaries state that they come directly from SCOWL and are under SCOWL's
copyright. SCOWL's `Copyright` file, verbatim, with the notices of its components
(among them the UK Advanced Cryptics Dictionary's, which must be included
verbatim, and WordNet 1.6's):

    The collective work is Copyright 2000-2018 by Kevin Atkinson as well
    as any of the copyrights mentioned below:

      Copyright 2000-2018 by Kevin Atkinson

      Permission to use, copy, modify, distribute and sell these word
      lists, the associated scripts, the output created from the scripts,
      and its documentation for any purpose is hereby granted without fee,
      provided that the above copyright notice appears in all copies and
      that both that copyright notice and this permission notice appear in
      supporting documentation. Kevin Atkinson makes no representations
      about the suitability of this array for any purpose. It is provided
      "as is" without express or implied warranty.

    Alan Beale <biljir@pobox.com> also deserves special credit as he has,
    in addition to providing the 12Dicts package and being a major
    contributor to the ENABLE word list, given me an incredible amount of
    feedback and created a number of special lists (those found in the
    Supplement) in order to help improve the overall quality of SCOWL.

    The 10 level includes the 1000 most common English words (according to
    the Moby (TM) Words II [MWords] package), a subset of the 1000 most
    common words on the Internet (again, according to Moby Words II), and
    frequently class 16 from Brian Kelk's "UK English Wordlist
    with Frequency Classification".

    The MWords package was explicitly placed in the public domain:

        The Moby lexicon project is complete and has
        been place into the public domain. Use, sell,
        rework, excerpt and use in any way on any platform.

        Placing this material on internal or public servers is
        also encouraged. The compiler is not aware of any
        export restrictions so freely distribute world-wide.

        You can verify the public domain status by contacting

        Grady Ward
        3449 Martha Ct.
        Arcata, CA  95521-4884

        grady@netcom.com
        grady@northcoast.com

    The "UK English Wordlist With Frequency Classification" is also in the
    Public Domain:

      Date: Sat, 08 Jul 2000 20:27:21 +0100
      From: Brian Kelk <Brian.Kelk@cl.cam.ac.uk>

      > I was wondering what the copyright status of your "UK English
      > Wordlist With Frequency Classification" word list as it seems to
      > be lacking any copyright notice.

      There were many many sources in total, but any text marked
      "copyright" was avoided. Locally-written documentation was one
      source. An earlier version of the list resided in a filespace called
      PUBLIC on the University mainframe, because it was considered public
      domain.

      Date: Tue, 11 Jul 2000 19:31:34 +0100

      > So are you saying your word list is also in the public domain?

      That is the intention.

    The 20 level includes frequency classes 7-15 from Brian's word list.

    The 35 level includes frequency classes 2-6 and words appearing in at
    least 11 of 12 dictionaries as indicated in the 12Dicts package.  All
    words from the 12Dicts package have had likely inflections added via
    my inflection database.

    The 12Dicts package and Supplement is in the Public Domain.

    The WordNet database, which was used in the creation of the
    Inflections database, is under the following copyright:

      This software and database is being provided to you, the LICENSEE,
      by Princeton University under the following license.  By obtaining,
      using and/or copying this software and database, you agree that you
      have read, understood, and will comply with these terms and
      conditions.:

      Permission to use, copy, modify and distribute this software and
      database and its documentation for any purpose and without fee or
      royalty is hereby granted, provided that you agree to comply with
      the following copyright notice and statements, including the
      disclaimer, and that the same appear on ALL copies of the software,
      database and documentation, including modifications that you make
      for internal use or for distribution.

      WordNet 1.6 Copyright 1997 by Princeton University.  All rights
      reserved.

      THIS SOFTWARE AND DATABASE IS PROVIDED "AS IS" AND PRINCETON
      UNIVERSITY MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
      IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PRINCETON
      UNIVERSITY MAKES NO REPRESENTATIONS OR WARRANTIES OF MERCHANT-
      ABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF THE
      LICENSED SOFTWARE, DATABASE OR DOCUMENTATION WILL NOT INFRINGE ANY
      THIRD PARTY PATENTS, COPYRIGHTS, TRADEMARKS OR OTHER RIGHTS.

      The name of Princeton University or Princeton may not be used in
      advertising or publicity pertaining to distribution of the software
      and/or database.  Title to copyright in this software, database and
      any associated documentation shall at all times remain with
      Princeton University and LICENSEE agrees to preserve same.

    The 40 level includes words from Alan's 3esl list found in version 4.0
    of his 12dicts package.  Like his other stuff the 3esl list is also in the
    public domain.

    The 50 level includes Brian's frequency class 1, words appearing
    in at least 5 of 12 of the dictionaries as indicated in the 12Dicts
    package, and uppercase words in at least 4 of the previous 12
    dictionaries.  A decent number of proper names is also included: The
    top 1000 male, female, and Last names from the 1990 Census report; a
    list of names sent to me by Alan Beale; and a few names that I added
    myself.  Finally a small list of abbreviations not commonly found in
    other word lists is included.

    The name files form the Census report is a government document which I
    don't think can be copyrighted.

    The file special-jargon.50 uses common.lst and word.lst from the
    "Unofficial Jargon File Word Lists" which is derived from "The Jargon
    File".  All of which is in the Public Domain.  This file also contain
    a few extra UNIX terms which are found in the file "unix-terms" in the
    special/ directory.

    The 55 level includes words from Alan's 2of4brif list found in version
    4.0 of his 12dicts package.  Like his other stuff the 2of4brif is also
    in the public domain.

    The 60 level includes all words appearing in at least 2 of the 12
    dictionaries as indicated by the 12Dicts package.

    The 70 level includes Brian's frequency class 0 and the 74,550 common
    dictionary words from the MWords package.  The common dictionary words,
    like those from the 12Dicts package, have had all likely inflections
    added.  The 70 level also included the 5desk list from version 4.0 of
    the 12Dics package which is in the public domain.

    The 80 level includes the ENABLE word list, all the lists in the
    ENABLE supplement package (except for ABLE), the "UK Advanced Cryptics
    Dictionary" (UKACD), the list of signature words from the YAWL package,
    and the 10,196 places list from the MWords package.

    The ENABLE package, mainted by M\Cooper <thegrendel@theriver.com>,
    is in the Public Domain:

      The ENABLE master word list, WORD.LST, is herewith formally released
      into the Public Domain. Anyone is free to use it or distribute it in
      any manner they see fit. No fee or registration is required for its
      use nor are "contributions" solicited (if you feel you absolutely
      must contribute something for your own peace of mind, the authors of
      the ENABLE list ask that you make a donation on their behalf to your
      favorite charity). This word list is our gift to the Scrabble
      community, as an alternate to "official" word lists. Game designers
      may feel free to incorporate the WORD.LST into their games. Please
      mention the source and credit us as originators of the list. Note
      that if you, as a game designer, use the WORD.LST in your product,
      you may still copyright and protect your product, but you may *not*
      legally copyright or in any way restrict redistribution of the
      WORD.LST portion of your product. This *may* under law restrict your
      rights to restrict your users' rights, but that is only fair.

    UKACD, by J Ross Beresford <ross@bryson.demon.co.uk>, is under the
    following copyright:

      Copyright (c) J Ross Beresford 1993-1999. All Rights Reserved.

      The following restriction is placed on the use of this publication:
      if The UK Advanced Cryptics Dictionary is used in a software package
      or redistributed in any form, the copyright notice must be
      prominently displayed and the text of this document must be included
      verbatim.

      There are no other restrictions: I would like to see the list
      distributed as widely as possible.

    The 95 level includes the 354,984 single words, 256,772 compound
    words, 4,946 female names and the 3,897 male names, and 21,986 names
    from the MWords package, ABLE.LST from the ENABLE Supplement, and some
    additional words found in my part-of-speech database that were not
    found anywhere else.

    Accent information was taken from UKACD.

    The VarCon package was used to create the American, British, Canadian,
    and Australian word list.  It is under the following copyright:

      Copyright 2000-2016 by Kevin Atkinson

      Permission to use, copy, modify, distribute and sell this array, the
      associated software, and its documentation for any purpose is hereby
      granted without fee, provided that the above copyright notice appears
      in all copies and that both that copyright notice and this permission
      notice appear in supporting documentation. Kevin Atkinson makes no
      representations about the suitability of this array for any
      purpose. It is provided "as is" without express or implied warranty.

      Copyright 2016 by Benjamin Titze

      Permission to use, copy, modify, distribute and sell this array, the
      associated software, and its documentation for any purpose is hereby
      granted without fee, provided that the above copyright notice appears
      in all copies and that both that copyright notice and this permission
      notice appear in supporting documentation. Benjamin Titze makes no
      representations about the suitability of this array for any
      purpose. It is provided "as is" without express or implied warranty.

      Since the original words lists come from the Ispell distribution:

      Copyright 1993, Geoff Kuenning, Granada Hills, CA
      All rights reserved.

      Redistribution and use in source and binary forms, with or without
      modification, are permitted provided that the following conditions
      are met:

      1. Redistributions of source code must retain the above copyright
         notice, this list of conditions and the following disclaimer.
      2. Redistributions in binary form must reproduce the above copyright
         notice, this list of conditions and the following disclaimer in the
         documentation and/or other materials provided with the distribution.
      3. All modifications to the source code must be clearly marked as
         such.  Binary redistributions based on modified source code
         must be clearly marked as modified versions in the documentation
         and/or other materials provided with the distribution.
      (clause 4 removed with permission from Geoff Kuenning)
      5. The name of Geoff Kuenning may not be used to endorse or promote
         products derived from this software without specific prior
         written permission.

      THIS SOFTWARE IS PROVIDED BY GEOFF KUENNING AND CONTRIBUTORS ``AS IS'' AND
      ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
      IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
      ARE DISCLAIMED.  IN NO EVENT SHALL GEOFF KUENNING OR CONTRIBUTORS BE LIABLE
      FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
      DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
      OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
      HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
      LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
      OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
      SUCH DAMAGE.

## The en_GB dictionary (Marco A.G. Pinto and others)

The en_GB LibreOffice dictionary is 1 of the 4 behind `libreoffice`. Its README's
license statement and its credits for added place names, verbatim (lines 1 to 28,
153 to 172, and 215 of the README at LibreOffice dictionaries commit `f2ff9905`):

    This dictionary was initially based on a subset of the
    original English wordlist created by Kevin Atkinson for
    Pspell and Aspell, and thus is covered by his original
    LGPL licence.

    It has been extensively updated by David Bartlett, Brian Kelk,
    Andrew Brown and Marco A.G.Pinto:
     — Numerous Americanisms/spellings have been removed;
     — Missing words have been added;
     — Many errors have been corrected;
     — Compound hyphenated words have been added where appropriate;
     — Thousands of proper/places names have been added;
     — Thousands of possessives have been added;
     — Thousands of plurals have been added;
     — Thousands of duplicates have been removed.

    Valuable inputs to this process were received from many other
    people — far too numerous to name. Serious thanks to all for
    your greatly appreciated help.

    This wordlist is intended to be a good representation of
    current modern British English, and thus it should be a good
    basis for Commonwealth English in most countries of the world
    outside North America.

    The affix file has been created completely from scratch
    by David Bartlett and Andrew Brown, based on the published
    rules for MySpell and is also provided under the LGPL.
    [lines 29 to 152 omitted]
    2018-06-01+:
               — Added places from New Zealand/UK (England, Scotland, Wales & Northern Ireland):
                 On V2.61–2.64 I included tons of place names.
                 My scientist friend, Peter McGavin, told me that in NZ they use British, so I decided
                 to do something about it. I did the same for the UK. I searched on Wikipedia for “towns”,
                 “counties”, “villages”, “boroughs”, “suburbs”, etc. and based me on:
                  — https://en.wikipedia.org/wiki/List_of_towns_in_England;
                  — https://en.wikipedia.org/wiki/List_of_towns_in_New_Zealand;
                  — https://en.wikipedia.org/wiki/List_of_civil_parishes_in_England;
                  — https://en.wikipedia.org/wiki/List_of_civil_parishes_in_Scotland;
                  — https://en.wikipedia.org/wiki/List_of_places_in_Scotland;
                  — https://en.wikipedia.org/wiki/List_of_communities_in_Wales;
                  — https://en.wikipedia.org/wiki/Local_government_in_Wales;
                  — https://en.wikipedia.org/wiki/List_of_towns_and_villages_in_Northern_Ireland;
                  — https://en.wikipedia.org/wiki/Counties_of_Northern_Ireland;
                  — https://en.wikipedia.org/wiki/Category:Suburbs_in_New_Zealand;
                  — https://en.wikipedia.org/wiki/List_of_Church_of_Scotland_parishes.
                 Furthermore, added places sent to me by Peter C.:
                 © OpenStreetMap contributors: www.openstreetmap.org/copyright.
                 © The Clergy of the Church of England Database Project, 2005.
    [lines 173 to 214 omitted]
                 — Add phonetic suggestion (© 2000 Björn Jacke)

## ENABLE

`attested_by` names `enable` when the word is in the ENABLE word list. Its
authors ask to be credited as the originators of the list: Alan Beale, its
researcher and compiler, and M. Cooper, the package's maintainer. Its
public-domain statement, verbatim, as SCOWL 2020.12.07 carries its readme:

    The ENABLE master word list, WORD.LST, is herewith formally released
    into the Public Domain. Anyone is free to use it or distribute it in
    any manner they see fit. No fee or registration is required for its
    use nor are "contributions" solicited (if you feel you absolutely
    must contribute something for your own peace of mind, the authors of
    the ENABLE list ask that you make a donation on their behalf to your
    favorite charity). This word list is our gift to the Scrabble community,
    as an alternate to "official" word lists. Game designers may feel free
    to incorporate the WORD.LST into their games. Please mention the source
    and credit us as originators of the list. Note that if you, as a game
    designer, use the WORD.LST in your product, you may still copyright and
    protect your product, but you may *not* legally copyright or in any way
    restrict redistribution of the WORD.LST portion of your product. This
    *may* under law restrict your rights to restrict your users' rights,
    but that is only fair.

## wordfreq 3.1.1 (Robyn Speer), and SUBTLEX

`attested_by` names `wordfreq` when wordfreq 3.1.1 gives the word an English
frequency. wordfreq is by Robyn Speer: Robyn Speer. (2022). rspeer/wordfreq: v3.0
(v3.0.2). Zenodo. https://doi.org/10.5281/zenodo.7199437. The license section of
its README, verbatim, with the terms of the data it contains:

    ## License

    `wordfreq` is freely redistributable under the Apache license (see
    `LICENSE.txt`), and it includes data files that may be
    redistributed under a Creative Commons Attribution-ShareAlike 4.0
    license (<https://creativecommons.org/licenses/by-sa/4.0/>).

    `wordfreq` contains data extracted from Google Books Ngrams
    (<http://books.google.com/ngrams>) and Google Books Syntactic Ngrams
    (<http://commondatastorage.googleapis.com/books/syntactic-ngrams/index.html>).
    The terms of use of this data are:

        Ngram Viewer graphs and data may be freely used for any purpose, although
        acknowledgement of Google Books Ngram Viewer as the source, and inclusion
        of a link to http://books.google.com/ngrams, would be appreciated.

    `wordfreq` also contains data derived from the following Creative Commons-licensed
    sources:

    - The Leeds Internet Corpus, from the University of Leeds Centre for Translation
      Studies (<http://corpus.leeds.ac.uk/list.html>)

    - Wikipedia, the free encyclopedia (<http://www.wikipedia.org>)

    - ParaCrawl, a multilingual Web crawl (<https://paracrawl.eu>)

    It contains data from OPUS OpenSubtitles 2018
    (<http://opus.nlpl.eu/OpenSubtitles.php>), whose data originates from the
    OpenSubtitles project (<http://www.opensubtitles.org/>) and may be used with
    attribution to OpenSubtitles.

    It contains data from various SUBTLEX word lists: SUBTLEX-US, SUBTLEX-UK,
    SUBTLEX-CH, SUBTLEX-DE, and SUBTLEX-NL, created by Marc Brysbaert et al.
    (see citations below) and available at
    <http://crr.ugent.be/programs-data/subtitle-frequencies>.

    I (Robyn Speer) have obtained permission by e-mail from Marc Brysbaert to
    distribute these wordlists in wordfreq, to be used for any purpose, not just
    for academic use, under these conditions:

    - Wordfreq and code derived from it must credit the SUBTLEX authors.
    - It must remain clear that SUBTLEX is freely available data.

    These terms are similar to the Creative Commons Attribution-ShareAlike license.

    Some additional data was collected by a custom application that watches the
    streaming Twitter API, in accordance with Twitter's Developer Agreement &
    Policy. This software gives statistics about words that are commonly used on
    Twitter; it does not display or republish any Twitter content.

wordfreq's data includes the SUBTLEX word lists, created by Marc Brysbaert and his colleagues, which wordfreq distributes by the author's permission on 2 conditions: that wordfreq and code derived from it credit the SUBTLEX authors, and that it remain clear that SUBTLEX is freely available data. The page wordfreq's README names is no longer served; its last capture by the Internet Archive is https://web.archive.org/web/20231116144719/http://crr.ugent.be/programs-data/subtitle-frequencies (November 16, 2023). SUBTLEX-US is offered at https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus and SUBTLEX-UK at https://osf.io/zq49t/. The authors' current copies carry the license CC BY-NC-SA 4.0; this dataset's values come through wordfreq 3.1.1, under wordfreq's statement of the permission.

wordfreq's data includes the SUBTLEX word lists, created by Marc Brysbaert and his
colleagues, which wordfreq distributes by the author's permission on 2
conditions: that wordfreq and code derived from it credit the SUBTLEX authors, and
that it remain clear that SUBTLEX is freely available data. SUBTLEX-US is offered
at https://www.ugent.be/pp/experimentele-psychologie/en/research/documents/subtlexus
and SUBTLEX-UK at https://osf.io/zq49t/.

## The first build's discovery sources

The list's first build (December 2025 and January 2026) found candidate words in,
among others, the English Wiktionary, WordNet, the LibreOffice dictionaries,
ENABLE (all above), Wikipedia (text under CC BY-SA 4.0,
https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use), and the Google Books
Ngram corpus, English 1-grams (https://storage.googleapis.com/books/ngrams/books/datasetsv3.html),
whose export page states: "This compilation is licensed under a Creative Commons
Attribution 3.0 Unported License" (http://creativecommons.org/licenses/by/3.0/).
The records no longer carry the discovery log.
