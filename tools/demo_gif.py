"""Records the README's demo of the site, as a GIF.

    uv run --no-project --isolated --with playwright==1.58.0 python tools/demo_gif.py [site] [out]

It drives the site in Chrome (Playwright's channel "chrome"): a search, a
filter, the charts, and the record. It records the window and turns the
recording into a GIF with ffmpeg. The preview banner is hidden, and a drawn
pointer shows where each click lands. The site defaults to the review preview;
give the production address once it is published. Needs Chrome and ffmpeg.

The searches are chosen so that every word on screen is 1 of a short vetted
list of examples, and the text is typed faster than the search's pause, so no
search runs on a partial word.
"""

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SITE = sys.argv[1] if len(sys.argv) > 1 else "https://review.english-openlist.pages.dev"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/media/search-the-list.gif")
W, H = 1280, 800

# the searches, and every word they may show; each set was checked against
# the list, by prefix and by contents
FIRST, SECOND, THIRD = "aflat", "sinceri", "seminarist"
SHOWN = {"aflatoxin", "aflatoxins", "sincerities", "sincerity", "seminarist", "seminarists"}

# the banner hidden, and a pointer drawn where the mouse is
SETUP = """
addEventListener('DOMContentLoaded', () => {
  const style = document.createElement('style');
  style.textContent = `.preview{display:none!important}
    #demo-pointer{position:fixed;left:0;top:0;width:22px;height:22px;z-index:2147483647;pointer-events:none;
      transform:translate(-100px,-100px);transition:transform 40ms linear}
    #demo-pointer svg{width:22px;height:22px;filter:drop-shadow(0 1px 1px rgba(0,0,0,.35))}
    #demo-pointer.down::after{content:'';position:absolute;left:-13px;top:-13px;width:26px;height:26px;
      border-radius:50%;border:2px solid rgba(190,35,35,.75)}`;
  document.head.appendChild(style);
  const p = document.createElement('div');
  p.id = 'demo-pointer';
  p.innerHTML = '<svg viewBox="0 0 22 22"><path d="M2 1 L2 18 L6.5 13.8 L9.6 20.6 L12.4 19.4 L9.4 12.8 L15.5 12.6 Z" fill="#fff" stroke="#111" stroke-width="1.3" stroke-linejoin="round"/></svg>';
  document.body.appendChild(p);
  addEventListener('mousemove', (e) => { p.style.transform = `translate(${e.clientX - 2}px, ${e.clientY - 1}px)`; });
  addEventListener('mousedown', () => p.classList.add('down'));
  addEventListener('mouseup', () => setTimeout(() => p.classList.remove('down'), 180));
});
"""


def content_height(video, at: float) -> int:
    """The rows of the recording the page fills: the recorder pads the frame
    below the page with uniform gray, which the GIF leaves out."""
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{at:.2f}", "-i", str(video), "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], check=True, capture_output=True).stdout
    row = W * 3

    def padding(y: int) -> bool:
        # a row of 1 mid gray, give or take the video codec's noise
        line = raw[y * row:(y + 1) * row]
        px = [line[x:x + 3] for x in range(0, row, 3 * 16)]
        return all(100 < r < 160 and abs(r - g) < 6 and abs(g - b) < 6 and abs(r - px[0][0]) < 8 for r, g, b in px)

    y = len(raw) // row - 1
    while y > 0 and padding(y):
        y -= 1
    # the codec blurs the edge for a few rows; leave them out too
    return (y + 1 - 8) // 2 * 2


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="eol-demo-"))
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        ctx = browser.new_context(viewport={"width": W, "height": H}, color_scheme="light",
                                  record_video_dir=str(work), record_video_size={"width": W, "height": H})
        started = time.monotonic()
        ctx.add_init_script(SETUP)
        page = ctx.new_page()
        pointer = [W / 2, H / 2]

        def go_to(x, y, steps=22):
            page.mouse.move(x, y, steps=steps)
            pointer[:] = [x, y]

        def click(locator, pause=900):
            locator.scroll_into_view_if_needed()
            box = locator.bounding_box()
            go_to(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.wait_for_timeout(160)
            page.mouse.down()
            page.wait_for_timeout(90)
            page.mouse.up()
            page.wait_for_timeout(pause)

        def shown_words():
            return set(page.locator(".rows .row-word").all_inner_texts())

        def check(expected=None):
            words = shown_words()
            if not words <= SHOWN:
                raise SystemExit(f"the demo would show {len(words - SHOWN)} word(s) outside its list")
            if expected is not None and words != expected:
                raise SystemExit(f"expected {sorted(expected)}, saw {sorted(words)}")

        def type_search(text):
            field = page.locator("#q")
            click(field, 200)
            page.keyboard.press("Meta+A")
            page.keyboard.type(text, delay=40)
            page.wait_for_function(
                f"[...document.querySelectorAll('.rows .row-word')].every(e => e.textContent.includes('{text}'))")

        # the first search arrives in the address, so no other word is ever drawn
        page.goto(f"{SITE}/?q={FIRST}", wait_until="networkidle")
        page.wait_for_function("document.querySelectorAll('.rows .row-word').length > 0")
        check({w for w in SHOWN if w.startswith(FIRST)})
        page.mouse.move(*pointer)
        ready = time.monotonic() - started
        page.wait_for_timeout(1600)

        type_search(SECOND)
        check({w for w in SHOWN if w.startswith(SECOND)})
        page.wait_for_timeout(1500)

        type_search(THIRD)
        check({w for w in SHOWN if w.startswith(THIRD)})
        page.wait_for_timeout(900)
        click(page.locator(".modes label").filter(has_text="Contains"), 1300)
        check({w for w in SHOWN if THIRD in w})
        click(page.locator(".opt").filter(has_text="No model or engine").locator("input"), 1600)
        check()

        click(page.get_by_role("link", name="Charts").first, 300)
        page.wait_for_selector("figure.chart")
        page.mouse.move(*pointer)
        page.wait_for_timeout(1300)
        bars = page.locator(".cols-hit").nth(9)
        box = bars.bounding_box()
        go_to(box["x"] + box["width"] / 2, box["y"] + box["height"] - 6)
        page.wait_for_timeout(1300)
        for top in (620, 1240, 1860):
            page.evaluate(f"window.scrollTo({{ top: {top}, behavior: 'smooth' }})")
            page.wait_for_timeout(1500)

        click(page.get_by_role("link", name="Rule and record").first, 300)
        page.wait_for_selector("#record")
        page.mouse.move(*pointer)
        page.wait_for_timeout(1000)
        page.evaluate("document.querySelector('#record').scrollIntoView({ behavior: 'smooth' })")
        page.wait_for_timeout(2600)
        video = page.video.path()
        page.close()
        ctx.close()
        browser.close()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        height = content_height(video, ready + 1.0)
        graph = (f"fps=10,crop={W}:{height}:0:0,scale=960:-1:flags=lanczos,split[a][b];"
                 "[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(0.0, ready - 0.1):.2f}", "-i", str(video),
                        "-vf", graph, "-loop", "0", str(OUT)], check=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"{OUT}: {OUT.stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
