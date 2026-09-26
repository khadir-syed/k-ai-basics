"""Self-check for the web pages: every example shown on a page must be exactly
what the real demo code produces. Runs instantly, no network.
Run from the repo root with: python web/test_web.py
"""
import contextlib
import hashlib
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys

# Demos 01 and 05 use GPT-2 from Hugging Face's cache: never go online for it.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "09-pii-redaction"))
sys.path.insert(0, os.path.join(ROOT, "07-prompt-playground"))
sys.path.insert(0, os.path.join(ROOT, "03-agent-trace"))
sys.path.insert(0, os.path.join(ROOT, "02-mini-rag"))
sys.path.insert(0, os.path.join(ROOT, "04-router-playground"))
sys.path.insert(0, os.path.join(ROOT, "08-prompt-injection"))
sys.path.insert(0, os.path.join(ROOT, "10-multi-agent-handoff"))
sys.path.insert(0, os.path.join(ROOT, "06-hallucination-demo"))
sys.path.insert(0, os.path.join(ROOT, "05-context-window"))
sys.path.insert(0, os.path.join(ROOT, "01-tokenizer-playground"))
from redact import redact  # noqa: E402
import playground  # noqa: E402
import trace as agent  # noqa: E402  (Demo 03's trace.py, not Python's own)
import ask  # noqa: E402
import router  # noqa: E402
import inject  # noqa: E402
import handoff  # noqa: E402
import compare  # noqa: E402
import explore  # noqa: E402
import run as tokens_demo  # noqa: E402  (Demo 01's run.py)


def read(path):
    return open(os.path.join(HERE, path), encoding="utf-8").read()


def texts(pattern, page):
    return [html.unescape(re.sub(r"<[^>]+>", "", t)) for t in re.findall(pattern, page, re.S)]


def printed(fn, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        fn(*args)
    return out.getvalue().rstrip("\n")


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
examples = re.findall(r'<code class="ex-in">(.*?)</code>.*?<pre class="output ex-trace[^"]*">(.*?)</pre>', page, re.S)
assert len(examples) == 6, len(examples)
for question, shown in examples:
    question, shown = html.unescape(question), texts(r"(.*)", shown)[0]
    assert printed(agent.run_rule_based, question) == shown, (question, shown)

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

# ---- Demo 04 ----------------------------------------------------------------
page = read("04/index.html")
examples = re.findall(r'<code class="ex-in">(.*?)</code>.*?<pre class="output ex-trace[^"]*">(.*?)</pre>', page, re.S)
assert len(examples) == 6, len(examples)
for request, shown in examples:
    request, shown = html.unescape(request), texts(r"(.*)", shown)[0]
    assert printed(router.run_rule_based, request) == shown, (request, shown)
# The page lists exactly the router's skills.
assert re.findall(r"<li><b>(.*?)</b>", page) == [s["name"] for s in router.SKILLS]

chips = [html.unescape(c) for c in re.findall(r'data-try="(.*?)"', page)]
assert chips == [html.unescape(r) for r, _ in examples], chips

# ---- Demo 08 ----------------------------------------------------------------
page = read("08/index.html")
steps = re.findall(r'<li class="ex" data-doc="(.*?)" data-filter="(on|off)">.*?<pre class="output ex-trace[^"]*">(.*?)</pre>', page, re.S)
# The same 4 steps as the terminal version, in the same order.
assert [(d, f == "on") for d, f, _ in steps] == [
    ("1_ticket_clean.txt", True), ("2_ticket_injected.txt", False),
    ("2_ticket_injected.txt", True), ("3_webpage_reworded.txt", True)], steps
for doc, use_filter, shown in steps:
    assert printed(inject.run_path, doc, use_filter == "on", inject.mock_agent) == texts(r"(.*)", shown)[0], doc
# The try-it buttons load exactly the demo's documents.
docs = re.findall(r'data-doc="(.*?)" data-t="chip_', page)
assert docs == sorted(os.listdir(os.path.join(ROOT, "08-prompt-injection", "docs"))), docs
assert re.search(r'const DOCS = \[(.*?)\]', read("08/app.js")).group(1) == ", ".join(f'"{d}"' for d in docs)

# ---- Demo 10 ----------------------------------------------------------------
page = read("10/index.html")
examples = re.findall(
    r'<li class="ex" data-handoff="(json|text)">.*?<code class="ex-in">(.*?)</code>.*?<pre class="output ex-trace[^"]*">(.*?)</pre>',
    page, re.S)
assert len(examples) == 6, len(examples)
for fmt, report, shown in examples:
    report, shown = html.unescape(report), texts(r"(.*)", shown)[0]
    assert printed(handoff.run, report, fmt) == shown, (report, fmt, shown)

chips = [html.unescape(c) for c in re.findall(r'data-try="(.*?)"', page)]
assert chips == list(dict.fromkeys(html.unescape(r) for _, r, _ in examples)), chips

# The saved real-AI run: the page's claims about it must hold. The demo's own
# check passes it, "steps" really came back as a list of invented steps (the
# report gave none), and Triage really said "data loss".
draft_text = texts(r'<pre class="output" id="real-draft">(.*?)</pre>', page)[0]
draft, problem = handoff.check_json(draft_text)
assert problem is None, problem
assert isinstance(draft["steps"], list) and len(draft["steps"]) == 4, draft["steps"]
assert "step" not in texts(r'<code class="ex-in" id="real-report">(.*?)</code>', page)[0].lower()
assert "data loss" in texts(r'<pre class="output" id="real-triage">(.*?)</pre>', page)[0]
assert "26 September 2026" in page and "gpt-oss-20b" in page

# ---- Demo 06 ----------------------------------------------------------------
page = read("06/index.html")
files = re.findall(r'<li data-file="(.*?)">', page)
assert files == sorted(os.listdir(os.path.join(ROOT, "06-hallucination-demo", "docs"))), files
titles = dict(zip(files, texts(r'<li data-file=".*?">(.*?)</li>', page)))
examples = re.findall(r'<li class="ex">(.*?)</li>\s*(?=<li class="ex">|</ol>)', page, re.S)
assert len(examples) == 6, len(examples)
questions = [texts(r'<code class="ex-in">(.*?)</code>', ex)[0] for ex in examples]
chips = [html.unescape(c) for c in re.findall(r'data-try="(.*?)"', page)]
assert chips == questions, chips
# Every example shows both saved AI answers, and the page says when and which model.
for ex in examples:
    assert len(texts(r'<p class="ai-answer">(.*?)</p>', ex)) == 2, ex[:80]
note = texts(r'<p class="muted" data-t="recorded_note">(.*?)</p>', page)[0]
assert "26 September 2026" in note and "gpt-oss-20b" in note, note

# ponytail: compare.py needs scikit-learn, like Demo 02 above.
try:
    import sklearn  # noqa: F401
except ImportError:
    print("(scikit-learn not installed: skipped the Demo 06 look-up checks)")
else:
    chunks = compare.load_chunks()
    for question, ex in zip(questions, examples):
        evidence = compare.found(compare.rank_chunks(question, chunks))
        file, count = re.search(r'<div class="found" data-file="(.*?)" data-count="(\d+)">', ex).groups()
        assert int(count) == len(evidence), (question, count, len(evidence))
        if not evidence:
            assert file == "", question
            continue
        src, text, score = evidence[0]
        assert file == src, (question, src, file)
        assert texts(r'<p class="found-text">(.*?)</p>', ex) == [text], question
        assert texts(r'<p class="found-story">(.*?)</p>', ex) == [f"{titles[src]} · {score * 100:.1f}% match"], question

# ---- GPT-2's word lists (web/gpt2/, used by Demos 01 and 05) ----------------
# They must be the exact files gpt2.py's fingerprints expect.
gpt2 = read("gpt2/gpt2.py")
for name, key in (("merges.txt", "vocab_bpe_hash"), ("vocab.json", "encoder_json_hash")):
    digest = hashlib.sha256(open(os.path.join(HERE, "gpt2", name), "rb").read()).hexdigest()
    assert f'{key}="{digest}"' in gpt2, name

# ponytail: Demos 01 and 05 need transformers (01's guesses also need torch and
# the GPT-2 model, cached by running Demo 01 once). Run with Demo 01's .venv on.
try:
    from transformers import GPT2Tokenizer
    gpt2_tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
except Exception:  # not installed, or GPT-2 never downloaded
    gpt2_tokenizer = None
    print("(transformers or GPT-2 not available: skipped the Demo 01 and 05 token checks; "
          "run with 01-tokenizer-playground's .venv on)")

def letters(ids):
    """Letters cut across several tokens (a Hindi letter, an emoji), found the
    terminal's way: keep adding tokens until they decode without "�"."""
    found, group = [], []
    for token in ids:
        group.append(token)
        text = gpt2_tokenizer.decode(group)
        if "\ufffd" not in text:
            if len(group) > 1:
                found.append(text.replace(" ", "·"))
            group = []
    return found


def check_bricks(sentence, bricks):
    """The token bricks shown for sentence: GPT-2's real pieces and IDs, with
    each cut letter's pieces bracketed under that letter."""
    real = gpt2_tokenizer.encode(sentence)
    assert [int(i) for i in re.findall(r'<li data-id="(\d+)">', bricks)] == real, sentence
    assert texts(r'<code class="tok">(.*?)</code>', bricks) == \
        [gpt2_tokenizer.decode([t]).replace(" ", "·").replace("\n", "↵") for t in real], sentence
    assert texts(r'<span class="tok-letter">(.*?)</span>', bricks) == letters(real), sentence
    return real


# ---- Demo 01 ----------------------------------------------------------------
page = read("01/index.html")
# Examples hold lists of their own, so cut the page at each example's start.
examples = page.split('<p class="lesson"')[0].split('<li class="ex">')[1:]
assert len(examples) == 6, len(examples)
assert "26 September 2026" in texts(r'<p class="muted" data-t="recorded_note">(.*?)</p>', page)[0]
if gpt2_tokenizer:
    try:
        import torch  # noqa: F401
    except ImportError:
        torch = None
        print("(torch not installed: skipped checking Demo 01's saved guesses)")
    for ex in examples:
        sentence = texts(r'<code class="ex-in">(.*?)</code>', ex)[0]
        # The tokens: the same (piece, id) pairs run.py prints, with spaces shown as ·.
        real = check_bricks(sentence, ex.split('<ol class="matches')[0])
        assert texts(r'<span class="tok-count">(\d+)</span>', ex) == [str(len(real))], sentence
        if torch:
            # The saved guesses: exactly the top 5 run.py prints.
            printed_guesses = re.findall(r"^(.*?)\s+#+\s+([\d.]+)%$", printed(tokens_demo.run, sentence), re.M)
            shown = list(zip(texts(r'<span class="match-story">(.*?)</span>', ex),
                             texts(r'<span class="match-pct">([\d.]+)%</span>', ex)))
            assert shown == printed_guesses, (sentence, shown, printed_guesses)
            assert re.findall(r'value="([\d.]+)"', ex) == [p for _, p in printed_guesses], sentence

    # The Hindi example really is bracketed into its 6 letters, 2 tokens each.
    assert texts(r'<span class="tok-letter">(.*?)</span>', page) == list("नमस्ते"), "Hindi letters"

# ---- Demo 05 ----------------------------------------------------------------
page = read("05/index.html")
budget = int(re.search(r'id="example" data-budget="(\d+)"', page).group(1))
assert budget == explore.DEFAULT_BUDGET, budget
steps = re.findall(r'<li class="step" data-tokens="(\d+)" data-used="(\d+)">(.*?)</li>', page, re.S)
assert len(steps) == 4, len(steps)
chips = [html.unescape(c) for c in re.findall(r'data-try="(.*?)"', page)]
assert chips[:4] == [texts(r'<p class="step-msg">.*?<q class="msg">(.*?)</q>', st)[0] for _, _, st in steps], chips
if gpt2_tokenizer:
    # "How are tokens counted?": the example message's real tokens.
    counting = re.search(r'<div class="count-example" data-text="(.*?)">(.*?)</div>', page, re.S)
    message = html.unescape(counting.group(1))
    check_bricks(message, counting.group(2))
    assert f'"{message}" is {len(gpt2_tokenizer.encode(message))} tokens' in html.unescape(page), message
    window = []
    for tokens, used, step in steps:
        message = texts(r'<p class="step-msg">.*?<q class="msg">(.*?)</q>', step)[0]
        n = len(gpt2_tokenizer.encode(message))  # what explore.py counts for each line
        dropped = explore.add_message(window, message, n, budget)
        assert (int(tokens), int(used)) == (n, sum(t for _, t in window)), message
        assert texts(r'<p class="step-dropped">.*?<q class="msg">(.*?)</q>', step) == [t for t, _ in dropped], message
    assert texts(r'<ul class="still" id="example-still">(.*?)</ul>', page) and \
        re.findall(r'<q class="msg">(.*?)</q>', re.search(r'id="example-still">(.*?)</ul>', page, re.S).group(1)) == \
        [html.escape(t, quote=False) for t, _ in window]
    # The shopping-list button really is too big for the default notepad.
    assert len(gpt2_tokenizer.encode(chips[-1])) > budget, chips[-1]

# ---- All pages --------------------------------------------------------------
DEMOS = sorted(d for d in os.listdir(HERE) if re.fullmatch(r"\d\d", d))
assert DEMOS == ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"], DEMOS
# Every demo page uses the same pinned Pyodide, in its HTML and its app.js.
versions = set()
for demo in DEMOS:
    versions |= set(re.findall(r"pyodide(?:@|/v)([\d.]+)/", read(f"{demo}/index.html") + read(f"{demo}/app.js")))
versions |= set(re.findall(r"pyodide(?:@|/v)([\d.]+)/", read("gpt2/tokens.js")))
assert len(versions) == 1, versions

# The home page links to every demo page.
home = read("index.html")
for demo in DEMOS:
    assert f'href="{demo}/"' in home, demo

print("All checks passed.")
