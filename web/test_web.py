"""Self-check for the web pages: every example shown on a page must be exactly
what the real demo code produces. Runs instantly, no network.
Run from the repo root with: python web/test_web.py
"""
import contextlib
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "09-pii-redaction"))
sys.path.insert(0, os.path.join(ROOT, "07-prompt-playground"))
sys.path.insert(0, os.path.join(ROOT, "03-agent-trace"))
sys.path.insert(0, os.path.join(ROOT, "02-mini-rag"))
from redact import redact  # noqa: E402
import playground  # noqa: E402
import trace as agent  # noqa: E402  (Demo 03's trace.py, not Python's own)
import ask  # noqa: E402


def read(path):
    return open(os.path.join(HERE, path), encoding="utf-8").read()


def texts(pattern, page):
    return [html.unescape(re.sub(r"<[^>]+>", "", t)) for t in re.findall(pattern, page, re.S)]


# ---- Demo 09 ----------------------------------------------------------------
page = read("09/index.html")
examples = re.findall(r'<code class="ex-in">(.*?)</code>.*?<code class="ex-out[^"]*">(.*?)</code>', page, re.S)
assert len(examples) == 6, len(examples)
for shown_in, shown_out in examples:
    written, sees = html.unescape(shown_in), html.unescape(shown_out)
    assert redact(written)[0] == sees, (written, redact(written)[0], sees)

# Each ✅/❌ verdict matches what actually happened.
verdicts = re.findall(r'class="ex-why (caught|missed)"', page)
for (shown_in, _), verdict in zip(examples, verdicts):
    hidden = redact(html.unescape(shown_in))[0] != html.unescape(shown_in)
    assert (verdict == "caught") == hidden, (shown_in, verdict)

# The tap-to-try buttons offer exactly the same 6 examples.
chips = [html.unescape(c) for c in re.findall(r'data-try="(.*?)"', page)]
assert chips == [html.unescape(i) for i, _ in examples], chips

# ---- Demo 07 ----------------------------------------------------------------
page = read("07/index.html")
pairs = re.findall(r'<li class="ex pair">(.*?)</li>\s*(?=<li class="ex pair">|</ol>)', page, re.S)
assert len(pairs) == len(playground.PAIRS), len(pairs)
total = len(playground.CHECKS)
for shown, real in zip(pairs, playground.PAIRS):
    assert texts(r'<p class="ex-what"[^>]*>\d\. (.*?)</p>', shown) == [real["name"]], shown[:80]
    assert texts(r'<code class="prompt">(.*?)</code>', shown) == [real["vague"], real["improved"]], real["name"]
    assert texts(r"<li><b>(.*?)</li>", shown) == [f"{n}: {w}" for n, w in real["changes"]], real["name"]
    score = f'{playground.score(real["vague"])}/{total} → {playground.score(real["improved"])}/{total}'
    assert texts(r'<span class="score">(.*?)</span>', shown) == [score], (real["name"], score)

# The page names the model and date the answers really came from.
saved = json.load(open(os.path.join(ROOT, "07-prompt-playground", "saved_answers.json"), encoding="utf-8"))
note = texts(r'<p id="saved-note"[^>]*>(.*?)</p>', page)[0]
assert saved["model"].split("/")[-1] in note and saved["date"] in note, note
assert len(saved["pairs"]) == len(playground.PAIRS)

# The tap-to-try buttons offer the 4 vague prompts.
chips = [html.unescape(c) for c in re.findall(r'data-try="(.*?)"', page)]
assert chips == [p["vague"] for p in playground.PAIRS], chips

# The formatter (07/markdown.js) turns every saved answer into clean text: no
# Markdown symbols left over, and every word kept, in the same order.
# ponytail: needs node to run the JavaScript; skipped (with a note) without it.
FORMAT_CHECK = r"""
const M = require("./web/07/markdown.js");
const saved = require("./07-prompt-playground/saved_answers.json");
const words = (t) => t.match(/[\p{L}\p{N}]+/gu) || [];
for (const [i, pair] of saved.pairs.entries()) {
  for (const [side, raw] of Object.entries(pair)) {
    const shown = M.tree(raw).map(M.textOf).join("");
    const left = shown.match(/^\s*#{1,6}\s|\*\*|\||<br|^\s*-{3,}\s*$/m);
    if (left) throw new Error(`pair ${i + 1} ${side}: "${left[0]}" left over`);
    const expected = raw.replace(/<br\s*\/?>/gi, " ").replace(/^\s*\d+\.\s/gm, "");
    if (words(shown).join(" ") !== words(expected).join(" ")) throw new Error(`pair ${i + 1} ${side}: words changed`);
  }
}
"""
if shutil.which("node"):
    r = subprocess.run(["node", "-e", FORMAT_CHECK], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, [line for line in r.stderr.splitlines() if line.startswith("Error")]
else:
    print("(node not installed: skipped the answer-formatting check)")

# ---- Demo 03 ----------------------------------------------------------------
page = read("03/index.html")
examples = re.findall(r'<code class="ex-in">(.*?)</code>.*?<pre class="output ex-trace">(.*?)</pre>', page, re.S)
assert len(examples) == 6, len(examples)
for question, shown in examples:
    question, shown = html.unescape(question), texts(r"(.*)", shown)[0]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        agent.run_rule_based(question)
    assert out.getvalue().rstrip("\n") == shown, (question, out.getvalue(), shown)

chips = [html.unescape(c) for c in re.findall(r'data-try="(.*?)"', page)]
assert chips == [html.unescape(q) for q, _ in examples], chips

# ---- Demo 02 ----------------------------------------------------------------
page = read("02/index.html")
# The page's story list names exactly the story files in docs/.
files = re.findall(r'<li data-file="(.*?)">', page)
assert files == sorted(os.listdir(os.path.join(ROOT, "02-mini-rag", "docs"))), files
titles = dict(zip(files, texts(r'<li data-file=".*?">(.*?)</li>', page)))

examples = re.findall(
    r'<code class="ex-in">(.*?)</code>\s*</p>\s*<div class="found" data-file="(.*?)">(.*?)</div>', page, re.S)
assert len(examples) == 6, len(examples)
chips = [html.unescape(c) for c in re.findall(r'data-try="(.*?)"', page)]
assert chips == [html.unescape(q) for q, _, _ in examples], chips

# ponytail: ask.py needs scikit-learn; run this with Demo 02's .venv switched on.
try:
    import sklearn  # noqa: F401
except ImportError:
    print("(scikit-learn not installed: skipped the Demo 02 checks; run with 02-mini-rag's .venv on)")
else:
    chunks = ask.load_chunks()
    for question, file, found in examples:
        src, text, score = ask.rank_chunks(html.unescape(question), chunks)[0]
        if score == 0:
            assert file == "", (question, "expected nothing found")
            continue
        assert file == src, (question, src, file)
        assert texts(r'<p class="found-text">(.*?)</p>', found) == [text], question
        assert texts(r'<p class="found-story">(.*?)</p>', found) == [f"Found in: {titles[src]}"], question

# ---- All pages --------------------------------------------------------------
# Every demo page uses the same pinned Pyodide, in its HTML and its app.js.
versions = set()
for demo in ("02", "03", "07", "09"):
    versions |= set(re.findall(r"pyodide(?:@|/v)([\d.]+)/", read(f"{demo}/index.html") + read(f"{demo}/app.js")))
assert len(versions) == 1, versions

# The home page links to every demo page.
home = read("index.html")
for demo in ("02", "03", "07", "09"):
    assert f'href="{demo}/"' in home, demo

print("All checks passed.")
