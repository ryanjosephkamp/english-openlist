import { useState } from 'react';
import { Snippet } from '../components/Snippet.tsx';

const WORDS_URL =
  'https://huggingface.co/datasets/ryanjosephkamp/english-openlist/resolve/main/data/merged_valid_words.txt';

type Lang = 'python' | 'cli' | 'javascript' | 'sql' | 'rust';

const LANGS: { readonly value: Lang; readonly label: string }[] = [
  { value: 'python', label: 'Python' },
  { value: 'cli', label: 'Command line' },
  { value: 'javascript', label: 'JavaScript' },
  { value: 'sql', label: 'SQL / DuckDB' },
  { value: 'rust', label: 'Rust' },
];

export function UsePage() {
  const [lang, setLang] = useState<Lang>('python');

  return (
    <div className="flex flex-col gap-12">
      <section className="flex flex-col gap-4">
        <h1 className="font-display text-3xl tracking-tight sm:text-4xl">
          Use it in your own thing
        </h1>
        <p className="max-w-[62ch] text-ink-soft">
          The list is one word per line, UTF-8, sorted, 4.4 MB. There is no API to sign up for and
          no key to manage — it is a file at a URL, and every snippet below was run before it was
          published, with the output it produced.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="label">The only URL you need</h2>
        <Snippet id="url" code={WORDS_URL} />
        <p className="max-w-[62ch] text-sm text-ink-soft">
          Sorted by byte order, one word per line, no header, no BOM. 345,297 lines. Two of them
          are not ASCII (<code className="font-mono text-xs">norteño</code> and{' '}
          <code className="font-mono text-xs">peléan</code>) and 188 contain a hyphen, so read it as
          UTF-8 and do not assume <code className="font-mono text-xs">[a-z]</code>.
        </p>
      </section>

      <section className="flex flex-col gap-5">
        <div
          role="tablist"
          aria-label="Language"
          className="flex flex-wrap divide-x divide-rule overflow-hidden rounded-[3px] border border-rule bg-surface"
        >
          {LANGS.map((option) => (
            <button
              key={option.value}
              type="button"
              role="tab"
              aria-selected={lang === option.value}
              onClick={() => setLang(option.value)}
              className={`h-[34px] px-3 text-sm transition-colors duration-150 ${
                lang === option.value
                  ? 'bg-accent-wash text-accent'
                  : 'text-ink-soft hover:bg-sunken hover:text-ink'
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-8">
          {lang === 'python' && <Python />}
          {lang === 'cli' && <Cli />}
          {lang === 'javascript' && <JavaScript />}
          {lang === 'sql' && <Sql />}
          {lang === 'rust' && <Rust />}
        </div>
      </section>

      <Recipes />
      <GameArtifacts />
    </div>
  );
}

/**
 * The per-length answer sets the pipeline already publishes.
 *
 * They are regenerated every night, cover lengths 2 through 35, and are
 * currently reachable only by knowing the path — no page anywhere links to
 * them. For anyone building a word game they are the most immediately useful
 * thing in the dataset.
 */
function GameArtifacts() {
  return (
    <section className="flex flex-col gap-6 border-t border-rule-strong pt-10">
      <div className="flex flex-col gap-2">
        <h2 className="font-display text-2xl tracking-tight">
          Building a word game? Start here instead
        </h2>
        <p className="max-w-[64ch] text-sm text-ink-soft">
          The pipeline generates curated answer sets every night for every length from 2 to 35, so
          you do not have to pick answers out of 345,297 words yourself. Each file holds a
          deterministic stratified sample as <code className="font-mono text-xs">answers</code> and
          the complete list for that length as <code className="font-mono text-xs">validGuesses</code>
          . Length 5 gives you 2,175 answers against 9,777 accepted guesses.
        </p>
      </div>

      <Snippet
        id="brrrdle"
        title="Every length, one URL pattern"
        note="Answers are sampled by starting letter and a quality score — frequency, letter position, vowel balance, uniqueness — with seed 42 + length, so the same file is reproducible."
        code={`BASE = ("https://huggingface.co/datasets/ryanjosephkamp/"
        "english-openlist/resolve/main/data/brrrdle")

# words_length_2.json ... words_length_35.json
import json, urllib.request

with urllib.request.urlopen(f"{BASE}/words_length_5.json") as r:
    data = json.load(r)

answers = data["answers"]              # curated, playable
guesses = set(data["validGuesses"])    # everything accepted

print(len(answers), len(guesses))
print(data["metadata"]["curation"]["seed"])`}
        output={`2175 9777
47`}
      />

      <p className="max-w-[64ch] text-sm text-ink-soft">
        The legacy <code className="font-mono text-xs">brrrdle_words.txt</code> and{' '}
        <code className="font-mono text-xs">brrrdle_words.json</code> in the same folder are
        length-5 only and are scheduled for removal. Build against{' '}
        <code className="font-mono text-xs">words_length_&#123;N&#125;.json</code>.
      </p>
    </section>
  );
}

function Python() {
  return (
    <>
      <Snippet
        id="py-datasets"
        title="With Hugging Face datasets"
        note="The default configuration is the valid word list, one word per row in a text column."
        code={`from datasets import load_dataset

ds = load_dataset("ryanjosephkamp/english-openlist", split="train")

print(ds.num_rows, ds.column_names)
print([r["text"] for r in ds.select(range(5))])`}
        output={`345297 ['text']
['a', 'aa', 'aah', 'aahed', 'aahing']`}
      />

      <Snippet
        id="py-hub"
        title="Just the file"
        note="Usually what you want for a word list — no Arrow, no schema, just a set of strings."
        code={`from huggingface_hub import hf_hub_download

path = hf_hub_download(
    "ryanjosephkamp/english-openlist",
    "data/merged_valid_words.txt",
    repo_type="dataset",
)
words = set(open(path, encoding="utf-8").read().split())

print(len(words))
print("hello" in words, "asdf" in words)`}
        output={`345297
True False`}
      />

      <Snippet
        id="py-pandas"
        title="With pandas"
        note="keep_default_na and na_filter matter here: without them pandas reads the word “null” as a missing value."
        code={`import pandas as pd

URL = "${WORDS_URL}"
words = pd.read_csv(URL, header=None, names=["word"],
                    keep_default_na=False, na_filter=False)

print(words.shape)
print(words.word.str.len().mean())`}
        output={`(345297, 1)
10.71414206196505`}
      />
    </>
  );
}

function Cli() {
  return (
    <>
      <Snippet
        id="cli-curl"
        title="curl"
        note="The -L is required. The resolve URL answers with a 307 to a CDN host, and without it you get a 315-byte redirect body instead of the list."
        code={`curl -L -o english-openlist.txt \\
  "${WORDS_URL}"

wc -l english-openlist.txt`}
        output={`345297 english-openlist.txt`}
      />

      <Snippet
        id="cli-hf"
        title="Hugging Face CLI"
        note="Caches under ~/.cache/huggingface and prints the path it wrote."
        code={`hf download ryanjosephkamp/english-openlist \\
  data/merged_valid_words.txt --repo-type dataset`}
        output={`/Users/you/.cache/huggingface/hub/datasets--ryanjosephkamp--english-openlist/
  snapshots/dfa8acce.../data/merged_valid_words.txt`}
      />

      <Snippet
        id="cli-peek"
        title="Look without downloading"
        note="The CDN honours HTTP range requests, so you can sample a 4.4 MB file — or the 12.2 GB one — without pulling it."
        code={`curl -sL -r 0-40 "${WORDS_URL}"`}
        output={`a
aa
aah
aahed
aahing`}
      />
    </>
  );
}

function JavaScript() {
  return (
    <>
      <Snippet
        id="js-fetch"
        title="fetch"
        note="Works in Node 18+, Deno, Bun and the browser. The response is plain text; filter the empty trailing line."
        code={`const URL =
  "${WORDS_URL}";

const res = await fetch(URL);
const words = new Set((await res.text()).split("\\n").filter(Boolean));

console.log(words.size, words.has("hello"), words.has("asdf"));`}
        output={`345297 true false`}
      />

      <Snippet
        id="js-note"
        title="A note on shipping this to browsers"
        note="4.4 MB of text is a lot to send a visitor. This site ships the same 345,297 words in 508 KB by front-coding them and serving brotli — the encoder is MIT licensed and in the repo at packages/wordlist."
        code={`// Cheapest useful version: let the server compress it.
// gzip takes the raw list to 1.02 MB, brotli to 856 KB.
// Front-coding first (each word stores only what it does not
// share with the previous one) takes brotli to 508 KB.`}
      />
    </>
  );
}

function Sql() {
  return (
    <>
      <Snippet
        id="sql-duckdb"
        title="DuckDB, straight over HTTPS"
        note="No download step. DuckDB streams the file and you query it like a table."
        code={`INSTALL httpfs; LOAD httpfs;

CREATE TABLE words AS
SELECT column0 AS word
FROM read_csv('${WORDS_URL}',
              header = false, columns = {'column0': 'VARCHAR'});

SELECT count(*) FROM words;
SELECT count(*) FROM words WHERE length(word) = 5;
SELECT count(*) FROM words WHERE word LIKE 'q%' AND word NOT LIKE 'qu%';
SELECT word FROM words ORDER BY length(word) DESC LIMIT 1;`}
        output={`345297
9785
135
phosphoribosylaminoimidazolesuccinocarboxamides`}
      />

      <Snippet
        id="sql-parquet"
        title="Or the auto-converted Parquet"
        note="Hugging Face keeps a Parquet copy of the default config. It is 2.85 MB. Load it into a table once rather than querying the URL repeatedly — each query refetches, and the endpoint will answer 429."
        code={`CREATE TABLE words AS
SELECT text AS word
FROM 'hf://datasets/ryanjosephkamp/english-openlist@~parquet/default/train/*.parquet';

SELECT count(*) FROM words;`}
        output={`345297`}
      />
    </>
  );
}

function Rust() {
  return (
    <Snippet
      id="rust"
      title="Rust"
      note="One dependency: cargo add ureq."
      code={`use std::collections::HashSet;

const URL: &str = "${WORDS_URL}";

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let body = ureq::get(URL).call()?.body_mut().read_to_string()?;
    let words: HashSet<&str> = body.lines().collect();

    println!("{} words", words.len());
    println!("hello: {}", words.contains("hello"));
    println!("asdf:  {}", words.contains("asdf"));
    Ok(())
}`}
      output={`345297 words
hello: true
asdf:  false`}
    />
  );
}

function Recipes() {
  return (
    <section className="flex flex-col gap-6 border-t border-rule-strong pt-10">
      <div className="flex flex-col gap-2">
        <h2 className="font-display text-2xl tracking-tight">Four things people build with this</h2>
        <p className="max-w-[62ch] text-sm text-ink-soft">
          Complete and runnable rather than sketched. Each was executed against the real list.
        </p>
      </div>

      <Snippet
        id="recipe-spell"
        title="A spell-checker that suggests"
        note="Set membership for the check, edit distance one for the suggestion. At this size no index is needed — the intersection against 345,297 words is instant."
        code={`words = set(open("english-openlist.txt", encoding="utf-8").read().split())
ALPHABET = "abcdefghijklmnopqrstuvwxyz"

def edits1(word):
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    return {
        *(a + b[1:] for a, b in splits if b),                           # delete
        *(a + b[1] + b[0] + b[2:] for a, b in splits if len(b) > 1),    # transpose
        *(a + c + b[1:] for a, b in splits if b for c in ALPHABET),     # replace
        *(a + c + b for a, b in splits for c in ALPHABET),              # insert
    }

def suggest(word):
    return [] if word in words else sorted(edits1(word) & words)

for probe in ["recieve", "teh", "wrod", "hello"]:
    print(f"{probe!r:10} -> {suggest(probe)[:5]}")`}
        output={`'recieve'  -> ['receive', 'relieve']
'teh'      -> ['eh', 'eth', 'feh', 'heh', 'peh']
'wrod'     -> ['prod', 'rod', 'trod', 'wood', 'word']
'hello'    -> []`}
      />

      <Snippet
        id="recipe-wordle"
        title="A Wordle-style answer list"
        note="The pipeline already publishes curated per-length sets for lengths 2 to 35, so you do not have to build one. Length 5 has 2,175 curated answers and 9,777 valid guesses."
        code={`import json, urllib.request

BASE = ("https://huggingface.co/datasets/ryanjosephkamp/"
        "english-openlist/resolve/main/data/brrrdle")

with urllib.request.urlopen(f"{BASE}/words_length_5.json") as r:
    data = json.load(r)

print(len(data["answers"]), "answers")
print(len(data["validGuesses"]), "valid guesses")
print(data["answers"][:5])`}
        output={`2175 answers
9777 valid guesses
['abbes', 'abets', 'abled', 'abler', 'ables']`}
      />

      <Snippet
        id="recipe-filter"
        title="Filtering by where a word came from"
        note="The metadata file is 291 MB and json.load holds roughly 2 GB while parsing it. That is fine on a laptop and not fine in a small container — if you only want the filtered list, take the prebuilt one below instead."
        code={`import json
from huggingface_hub import hf_hub_download

path = hf_hub_download(
    "ryanjosephkamp/english-openlist",
    "data/merged_valid_dict.json",
    repo_type="dataset",
)
with open(path, encoding="utf-8") as f:
    entries = json.load(f)

twl = {w for w, e in entries.items()
       if e.get("source") == "twl_scrabble_dictionary"}
human = {w for w, e in entries.items()
         if e.get("source") != "synthetic_generation"}

print(len(twl), "tournament words")
print(len(human), "words a human source attested")`}
        output={`175501 tournament words
314054 words a human source attested`}
      />

      <Snippet
        id="recipe-prebuilt"
        title="…or skip the 291 MB entirely"
        note="This site rebuilds both filtered lists every deploy, straight from the live dataset. Plain text, one word per line, same format as the full list."
        code={`curl -L -O https://english-openlist.pages.dev/downloads/human-attested.txt
curl -L -O https://english-openlist.pages.dev/downloads/tournament.txt

wc -l human-attested.txt tournament.txt`}
        output={`  314054 human-attested.txt
  175501 tournament.txt`}
      />
    </section>
  );
}
