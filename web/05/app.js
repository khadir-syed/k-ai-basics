// Runs Demo 05's real forgetting rule (add_message in
// 05-context-window/explore.py) inside the browser with Pyodide. Tokens are
// counted the way GPT-2 does, from GPT-2's own token list (see ../gpt2/, and
// tokens.js there) — the terminal version counts them the same way with
// transformers. Nothing is sent
// anywhere, and the page never talks to an AI. All page text is in index.html.
"use strict";

const DEMO = "../../05-context-window/";
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";
const $ = (id) => document.getElementById(id);

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.text();
}

async function loadPython() {
  const py = await loadPyodide({ indexURL: PYODIDE_URL, packageBaseUrl: GPT2_PACKAGES_URL });
  const pieces = await loadGpt2(py, fetchText);
  py.FS.mkdirTree("/demo");
  py.FS.writeFile("/demo/explore.py", await fetchText(DEMO + "explore.py"));
  // count() is what explore.py does with each message: len(tokenizer.encode(line)).
  py.runPython(`
sys.path.insert(0, "/demo")
import explore
def count(text):
    return len(_gpt2.encode(text))
def new_window():
    return []
`);
  return { py, pieces };
}

// One chat: a notepad (the demo's own window list) with a size (budget).
function makeChat(py) {
  const add = py.globals.get("explore").add_message;
  const count = py.globals.get("count");
  const newWindow = py.globals.get("new_window");
  return (budget) => {
    const window = newWindow();
    return {
      budget,
      // Returns { tokens, dropped: [[text, tokens]...] } or { tokens, tooBig: true }.
      send(text) {
        const tokens = count(text);
        const dropped = add(window, text, tokens, budget);
        if (dropped === undefined) return { tokens, tooBig: true }; // add_message returned None
        const out = { tokens, dropped: dropped.toJs() };
        dropped.destroy();
        return out;
      },
      remembered() {
        return window.toJs();
      },
    };
  };
}

// The example on the page was made by the terminal version. Replay it here
// through the real code, so the page can never quietly lie.
function checkExample(startChat, pieces) {
  const counting = document.querySelector("#counting .count-example");
  const countingOk = sameTokens(counting.querySelector(".tokens"), pieces(counting.dataset.text));
  const ex = $("example");
  const chat = startChat(Number(ex.dataset.budget));
  let ok = true;
  for (const step of ex.querySelectorAll(".step")) {
    const res = chat.send(step.querySelector(".step-msg .msg").textContent);
    const used = chat.remembered().reduce((sum, [, t]) => sum + t, 0);
    const shownGone = [...step.querySelectorAll(".step-dropped .msg")].map((q) => q.textContent);
    ok &&= !res.tooBig && String(res.tokens) === step.dataset.tokens && String(used) === step.dataset.used &&
      JSON.stringify(res.dropped.map(([text]) => text)) === JSON.stringify(shownGone);
  }
  const still = [...$("example-still").querySelectorAll(".msg")].map((q) => q.textContent);
  ok &&= JSON.stringify(chat.remembered().map(([text]) => text)) === JSON.stringify(still);
  if (!ok) {
    ex.classList.add("ex-stale");
    ex.querySelector(".ex-why").prepend("⚠ ");
  }
  if (!countingOk) counting.classList.add("ex-stale");
  ok &&= countingOk;
  const live = $("examples-live");
  live.textContent = ok ? live.dataset.ok : live.dataset.bad;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

const fill = (template, values) => template.replace(/\{(\w+)\}/g, (_, k) => values[k]);
// "1 token", but "2 tokens": each template has a -one twin for 1.
const tokensText = (t, key, n) => (n === 1 ? t[`${key}One`] : fill(t[key], { n }));

function messageList(className, items, t) {
  const list = el("ul", className);
  for (const [text, tokens] of items) {
    const li = el("li");
    li.append(el("q", "msg", text), " ", el("span", "step-n", tokensText(t, "tokens", tokens)));
    list.append(li);
  }
  return list;
}

// Draw the notepad after the last message: what happened, how full it is,
// what the AI can still see, and what it has already forgotten.
function draw(chat, last, forgotten, pieces) {
  const box = $("notepad");
  const t = box.dataset;
  box.replaceChildren();
  if (last) {
    const event = el("div", "step");
    const msg = el("p", "step-msg");
    msg.append(el("q", "msg", last.text), " ", el("span", "step-n", tokensText(t, "added", last.tokens)));
    event.append(msg, el("p", "try-label", t.pieces), drawTokens(pieces(last.text)));
    if (last.tooBig) event.append(el("p", "step-dropped", fill(t.toobig, { n: last.tokens, budget: chat.budget })));
    else if (last.dropped.length) {
      event.append(el("p", "step-dropped", t.rubbed), messageList("still gone", last.dropped, t));
    }
    box.append(event);
  }
  const kept = chat.remembered();
  const used = kept.reduce((sum, [, n]) => sum + n, 0);
  const meter = el("progress", "meter");
  meter.max = chat.budget;
  meter.value = used;
  const usedLine = el("p", "step-used");
  usedLine.append(meter, " ", el("span", "", fill(t.used, { used, budget: chat.budget, count: kept.length })));
  box.append(usedLine);
  if (!kept.length) box.append(el("p", "muted", t.empty));
  else box.append(el("p", "side-head", t.still), messageList("still", kept, t));
  if (forgotten.length) box.append(el("p", "side-head", t.gone), messageList("still gone", forgotten, t));
}

async function main() {
  const status = $("status");
  status.textContent = status.dataset.loading;
  let py, pieces;
  try {
    ({ py, pieces } = await loadPython());
  } catch (err) {
    status.textContent = status.dataset.failed;
    console.error(err);
    return;
  }
  status.textContent = "";
  const startChat = makeChat(py);
  checkExample(startChat, pieces);

  const box = $("try");
  const budget = $("budget");
  let chat, forgotten;
  const restart = () => {
    chat = startChat(Number(budget.value));
    forgotten = [];
    draw(chat, null, forgotten, pieces);
  };
  const send = (text) => {
    text = text.trim();
    if (!text) return;
    const res = chat.send(text);
    if (!res.tooBig) forgotten.push(...res.dropped);
    draw(chat, { text, ...res }, forgotten, pieces);
    box.value = "";
  };
  restart();

  for (const control of [box, budget, $("send"), $("restart")]) control.disabled = false;
  budget.addEventListener("change", restart);
  $("restart").addEventListener("click", restart);
  $("send").addEventListener("click", () => send(box.value));
  box.addEventListener("keydown", (e) => {
    if (e.key === "Enter") send(box.value);
  });
  for (const chip of document.querySelectorAll("#chips .chip-btn")) {
    chip.disabled = false;
    chip.addEventListener("click", () => send(chip.dataset.try));
  }
}

main();
