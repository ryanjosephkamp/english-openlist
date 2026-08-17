"""
The adjudication app — PROTOCOL.md §8.5.

Its one hard requirement is that the work is never repeated. Everything else
follows from that:

* **Append-only JSONL.** Every event — verdict, search click, amendment — is one
  line in `logs/<session>.jsonl`. Nothing is ever rewritten.
* **fsync before the UI advances.** The verdict endpoint fsyncs the log before
  returning 200, and the page only advances on 200. A power cut loses at most
  the verdict currently being clicked, never one that was shown as saved.
* **State by replay.** There is no state file. On startup the app replays every
  log in `logs/` and resumes at the first item without a verdict. Copy the
  directory to another machine and it resumes there — that is the whole
  recovery story, and it is also why the logs are committed to the private
  archive after each session.
* **Blinding is enforced by the app, not by discipline.** The deck file may
  carry `stratum`, `kind` (anchor / repeat / sample) and anything else the
  analysis needs; the client is sent the word and nothing but the word.
* **The timer is soft.** The per-item clock turns amber at 90 seconds
  (PROTOCOL.md §8.2's budget) and the session clock warns at 45 minutes;
  neither ever blocks or cuts.

Search instruments render in the fixed §8.2 order, and every click is logged
before the tab opens — that is how "was a search opened" becomes an observed
variable rather than a self-report. Query shapes follow §8.3: quoted-phrase
searches, never `define X`; the filtered web search excludes the detector
sources and word-list domains.

Verdicts (§8.4): yes / no / unsure. A misclick can be amended until the next
verdict is cast — the amendment is itself an append-only event, and replay
honours the last one. After that the verdict is final: revisiting adjudicated
items is exactly the repetition this app exists to prevent.

Run:
    python -m research.adjudicate.app --deck research/adjudicate/decks/practice.jsonl
Then open http://127.0.0.1:8377
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG_DIR = HERE / "logs"

#: §8.2, fixed order. Google Books first, deliberately: books are authored and
#: edited by construction, carry author/title/date for the G2 independence
#: check, and show snippet context for the G1 use-vs-mention call.
INSTRUMENTS = [
    ("books", "Google Books",
     "https://www.google.com/search?tbm=bks&q=%22{w}%22"),
    ("scholar", "Google Scholar",
     "https://scholar.google.com/scholar?q=%22{w}%22"),
    ("pubmed", "PubMed / PMC",
     "https://pubmed.ncbi.nlm.nih.gov/?term=%22{w}%22"),
    ("hathitrust", "HathiTrust",
     "https://babel.hathitrust.org/cgi/ls?anyall1=phrase;q1={w};field1=ocr;a=srchls;ft=ft"),
    ("web", "Filtered web",
     "https://www.google.com/search?q=%22{w}%22"
     "+-site:en.wiktionary.org+-site:wiktionary.org+-site:merriam-webster.com"
     "+-site:dictionary.com+-site:thefreedictionary.com+-site:wordnik.com"
     "+-site:collinsdictionary.com+-site:scrabblewordfinder.org"
     "+-site:wordfind.com+-site:thewordfinder.com"),
]

VERDICTS = {"yes", "no", "unsure"}


# ---------------------------------------------------------------------------
# Replay — the only source of state, and pure so it is testable.
# ---------------------------------------------------------------------------

def replay(log_lines) -> dict:
    """
    Fold an iterable of JSONL lines into the current state.

    Returns {"verdicts": {item_id: record}, "searched": {item_id: [slugs]}}.
    A `verdict_amend` replaces the verdict for its item; replay order is file
    order, so the last amendment wins, which is also the newest by fsync.
    """
    verdicts: dict[str, dict] = {}
    searched: dict[str, list] = {}
    for line in log_lines:
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        event = rec.get("event")
        item = rec.get("item_id")
        if event == "search":
            searched.setdefault(item, []).append(rec.get("instrument"))
        elif event in ("verdict", "verdict_amend"):
            verdicts[item] = rec
    return {"verdicts": verdicts, "searched": searched}


def load_state() -> dict:
    lines = []
    if LOG_DIR.exists():
        for path in sorted(LOG_DIR.glob("*.jsonl")):
            with open(path, encoding="utf-8") as f:
                lines.extend(f.readlines())
    return replay(lines)


def load_deck(path: Path) -> list[dict]:
    deck = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                deck.append(json.loads(line))
    ids = [d["id"] for d in deck]
    if len(ids) != len(set(ids)):
        raise SystemExit("deck has duplicate item ids — refusing to serve it")
    return deck


# ---------------------------------------------------------------------------
# Append-only log with fsync-before-advance
# ---------------------------------------------------------------------------

class SessionLog:
    def __init__(self, session_id: str):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.path = LOG_DIR / f"{session_id}.jsonl"
        self.session_id = session_id

    def append(self, record: dict) -> None:
        record = {"ts": datetime.now(timezone.utc).isoformat(),
                  "session": self.session_id, **record}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())   # durable BEFORE the UI is told to advance


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

PAGE = """<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>EOL adjudication</title>
<style>
  :root { --ink:#161a22; --soft:#6a7183; --rule:#dfe3ea; --accent:#2f4d7a;
          --yes:#3d6b52; --no:#8f3d2f; --warn:#a06515; --bg:#f7f8fa; }
  body { font-family: ui-sans-serif, system-ui; background:var(--bg);
         color:var(--ink); max-width:44rem; margin:0 auto; padding:2rem 1rem; }
  #word { font-size:3rem; font-family:ui-monospace,Menlo,monospace;
          text-align:center; margin:2.5rem 0 .5rem; word-break:break-all; }
  #clocks { text-align:center; color:var(--soft); font-variant-numeric:tabular-nums; }
  #item-clock.over { color:var(--warn); font-weight:700; }
  .row { display:flex; gap:.5rem; justify-content:center; flex-wrap:wrap; margin:1.2rem 0; }
  button { font-size:1rem; padding:.7rem 1.2rem; border:1px solid var(--rule);
           border-radius:4px; background:#fff; cursor:pointer; }
  .instr { font-size:.85rem; }
  .instr.used { border-color:var(--accent); color:var(--accent); font-weight:600; }
  #yes { background:var(--yes); color:#fff; border:none; }
  #no  { background:var(--no);  color:#fff; border:none; }
  #unsure { background:#fff; }
  #undo { font-size:.8rem; color:var(--soft); background:none; border:none;
          text-decoration:underline; }
  #banner { display:none; background:#fdf3e6; border:1px solid var(--warn);
            padding:.6rem 1rem; border-radius:4px; margin-bottom:1rem; }
  #progress { text-align:center; color:var(--soft); font-size:.85rem; }
  #done { display:none; text-align:center; font-size:1.4rem; margin-top:3rem; }
  kbd { background:#eceff4; border-radius:3px; padding:0 .35em; font-size:.85em; }
</style>
<div id="banner">45 minutes in this session — the timer is soft, but the
protocol suggests a break.</div>
<div id="progress"></div>
<div id="word"></div>
<div id="clocks"><span id="item-clock">0s</span> · session <span id="sess-clock">0m</span></div>
<div class="row" id="instruments"></div>
<div class="row">
  <button id="yes">yes <kbd>y</kbd></button>
  <button id="unsure">unsure <kbd>u</kbd></button>
  <button id="no">no <kbd>n</kbd></button>
</div>
<div class="row"><button id="undo" style="display:none">amend previous verdict</button></div>
<div id="done">Deck complete. Every verdict is on disk.</div>
<script>
let item = null, t0 = 0, sess0 = Date.now(), lastVerdictItem = null;
const $ = id => document.getElementById(id);

async function next() {
  const r = await fetch('/api/next');
  const d = await r.json();
  if (d.done) { $('word').style.display='none'; $('done').style.display='block';
                document.querySelectorAll('.row').forEach(e=>e.style.display='none');
                $('progress').textContent = d.total + ' / ' + d.total; return; }
  item = d.id; t0 = Date.now();
  $('word').textContent = d.word;
  $('progress').textContent = (d.position) + ' / ' + d.total;
  const box = $('instruments'); box.innerHTML = '';
  for (const [slug, label, url] of d.instruments) {
    const b = document.createElement('button');
    b.textContent = label; b.className = 'instr'; b.dataset.slug = slug;
    b.onclick = async () => {
      await fetch('/api/search', {method:'POST', body: JSON.stringify({item_id: item, instrument: slug})});
      b.classList.add('used');
      window.open(url, '_blank');
    };
    box.appendChild(b);
  }
  const esc = document.createElement('button');
  esc.textContent = 'other instrument (recorded)'; esc.className = 'instr';
  esc.onclick = async () => {
    await fetch('/api/search', {method:'POST', body: JSON.stringify({item_id: item, instrument: 'escalated'})});
    esc.classList.add('used');
  };
  box.appendChild(esc);
}

async function verdict(v) {
  if (!item) return;
  const r = await fetch('/api/verdict', {method:'POST',
    body: JSON.stringify({item_id: item, verdict: v, client_ms: Date.now()-t0})});
  if (!r.ok) { alert('NOT SAVED — verdict did not reach disk. Stopping.'); return; }
  lastVerdictItem = item; item = null;
  $('undo').style.display = 'inline';
  next();
}

$('undo').onclick = async () => {
  if (!lastVerdictItem) return;
  const v = prompt('Amend previous verdict to (yes / no / unsure):');
  if (!v || !['yes','no','unsure'].includes(v)) return;
  const r = await fetch('/api/amend', {method:'POST',
    body: JSON.stringify({item_id: lastVerdictItem, verdict: v})});
  if (r.ok) { $('undo').style.display='none'; }
};

$('yes').onclick = () => verdict('yes');
$('no').onclick = () => verdict('no');
$('unsure').onclick = () => verdict('unsure');
document.addEventListener('keydown', e => {
  if (e.key==='y') verdict('yes');
  if (e.key==='n') verdict('no');
  if (e.key==='u') verdict('unsure');
});
setInterval(() => {
  if (item) {
    const s = Math.floor((Date.now()-t0)/1000);
    const c = $('item-clock'); c.textContent = s + 's';
    c.className = s >= 90 ? 'over' : '';
  }
  const m = Math.floor((Date.now()-sess0)/60000);
  $('sess-clock').textContent = m + 'm';
  if (m >= 45) $('banner').style.display = 'block';
}, 1000);
next();
</script>
"""


def make_handler(deck: list[dict], log: SessionLog, state: dict):
    served_at: dict[str, float] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/":
                body = PAGE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path == "/api/next":
                done = state["verdicts"]
                for pos, entry in enumerate(deck, 1):
                    if entry["id"] not in done:
                        served_at[entry["id"]] = time.monotonic()
                        word = entry["word"]
                        self._json({
                            "id": entry["id"],
                            "word": word,          # the word, and nothing else
                            "position": pos,
                            "total": len(deck),
                            "instruments": [
                                (slug, label,
                                 url.format(w=urllib.parse.quote(word)))
                                for slug, label, url in INSTRUMENTS],
                        })
                        return
                self._json({"done": True, "total": len(deck)})
                return
            self._json({"error": "not found"}, 404)

        def _read_body(self) -> dict:
            n = int(self.headers.get("Content-Length", 0))
            return json.loads(self.rfile.read(n) or b"{}")

        def do_POST(self):
            body = self._read_body()
            item_id = body.get("item_id")
            if self.path == "/api/search":
                log.append({"event": "search", "item_id": item_id,
                            "instrument": body.get("instrument")})
                state["searched"].setdefault(item_id, []).append(
                    body.get("instrument"))
                self._json({"ok": True})
                return
            if self.path == "/api/verdict":
                v = body.get("verdict")
                if v not in VERDICTS:
                    self._json({"error": "bad verdict"}, 400)
                    return
                if item_id in state["verdicts"]:
                    # never repeated — a second verdict for a decided item is
                    # a client bug, and accepting it would corrupt the record
                    self._json({"error": "already adjudicated"}, 409)
                    return
                ms = None
                if item_id in served_at:
                    ms = int((time.monotonic() - served_at[item_id]) * 1000)
                rec = {"event": "verdict", "item_id": item_id, "verdict": v,
                       "ms": ms, "client_ms": body.get("client_ms"),
                       "searched": bool(state["searched"].get(item_id)),
                       "instruments": state["searched"].get(item_id, [])}
                log.append(rec)          # fsyncs before returning
                state["verdicts"][item_id] = rec
                self._json({"ok": True})
                return
            if self.path == "/api/amend":
                v = body.get("verdict")
                if v not in VERDICTS or item_id not in state["verdicts"]:
                    self._json({"error": "bad amend"}, 400)
                    return
                rec = {"event": "verdict_amend", "item_id": item_id,
                       "verdict": v,
                       "searched": bool(state["searched"].get(item_id)),
                       "instruments": state["searched"].get(item_id, [])}
                log.append(rec)
                state["verdicts"][item_id] = rec
                self._json({"ok": True})
                return
            self._json({"error": "not found"}, 404)

    return Handler


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", type=Path, required=True)
    ap.add_argument("--port", type=int, default=8377)
    args = ap.parse_args()

    deck = load_deck(args.deck)
    state = load_state()
    done = sum(1 for d in deck if d["id"] in state["verdicts"])
    session = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log = SessionLog(session)
    log.append({"event": "session_start", "deck": str(args.deck),
                "deck_size": len(deck), "already_adjudicated": done})

    print(f"deck: {len(deck)} items, {done} already adjudicated "
          f"(replayed from {LOG_DIR})")
    print(f"session log: {log.path}")
    print(f"open http://127.0.0.1:{args.port}")
    server = ThreadingHTTPServer(("127.0.0.1", args.port),
                                 make_handler(deck, log, state))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped. Remember to commit logs/ to the private archive.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
