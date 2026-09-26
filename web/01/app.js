// Splits text into tokens the way GPT-2 does, inside the browser with Pyodide.
// The terminal version (01-tokenizer-playground/run.py) needs the whole GPT-2
// model to guess the next token — about 500 MB, too big for a browser — so the
// guesses on this page were saved from a terminal run. The splitting runs live,
// from GPT-2's own token list (see ../gpt2/, and tokens.js there). Nothing is
// sent anywhere, and the page never talks to an AI. All page text is in
// index.html.
"use strict";

const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";
const $ = (id) => document.getElementById(id);

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.text();
}

// The 6 examples' tokens were made by the terminal version (transformers).
// Split them again here, so the page can never quietly disagree with it.
function checkExamples(pieces) {
  let allOk = true;
  for (const ex of document.querySelectorAll("#examples .ex")) {
    if (!sameTokens(ex.querySelector(".tokens"), pieces(ex.querySelector(".ex-in").textContent))) {
      allOk = false;
      ex.classList.add("ex-stale");
      ex.querySelector(".ex-why").prepend("⚠ ");
    }
  }
  const live = $("examples-live");
  live.textContent = allOk ? live.dataset.ok : live.dataset.bad;
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// Your sentence: how many tokens, the tokens themselves, and the ID numbers
// the AI really gets.
function tryOwn(pieces) {
  const out = $("try-output");
  out.replaceChildren();
  const text = $("try").value;
  if (!text.trim()) return;
  const groups = pieces(text);
  const ids = tokenIds(groups);
  const t = out.dataset;
  out.append(
    el("p", "tok-total", ids.length === 1 ? t.one : t.count.replace("{n}", ids.length)),
    drawTokens(groups),
    el("p", "try-label", t.sees),
    el("p", "tok-ids", ids.join(", ")),
  );
}

async function main() {
  const status = $("status");
  status.textContent = status.dataset.loading;
  let pieces;
  try {
    const py = await loadPyodide({ indexURL: PYODIDE_URL, packageBaseUrl: GPT2_PACKAGES_URL });
    pieces = await loadGpt2(py, fetchText);
  } catch (err) {
    status.textContent = status.dataset.failed;
    console.error(err);
    return;
  }
  status.textContent = "";
  checkExamples(pieces);

  const box = $("try");
  box.disabled = false;
  box.addEventListener("input", () => tryOwn(pieces));
  for (const chip of document.querySelectorAll("#chips .chip-btn")) {
    chip.disabled = false;
    chip.addEventListener("click", () => {
      box.value = chip.dataset.try;
      tryOwn(pieces);
      box.focus();
    });
  }
}

main();
