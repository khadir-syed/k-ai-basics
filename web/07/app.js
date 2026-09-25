// Runs Demo 07's real Python file (07-prompt-playground/playground.py) inside
// the browser with Pyodide, and shows the real AI answers saved in the repo
// (formatted by markdown.js).
// Nothing is sent anywhere: the page only downloads Pyodide and this repo's
// own files. It never talks to an AI. All page text is in index.html.
"use strict";

const DEMO = "../../07-prompt-playground/";
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";
const $ = (id) => document.getElementById(id);

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.text();
}

// Count words, not symbols: "|" and "---" from the AI's tables don't count.
const countWords = (text) => text.split(/\s+/).filter((w) => /[\p{L}\p{N}]/u.test(w)).length;

// Show the first few lines of an answer (as they appear on screen), and the
// rest behind "Show all". The 3-line cut itself is done in style.css.
function showAnswer(box, text) {
  const status = $("answers-status").dataset;
  const answer = document.createElement("div");
  answer.className = "md clamped";
  answer.append(...Markdown.tree(text).map(Markdown.toDom)); // markdown.js
  box.replaceChildren(answer);
  if (answer.scrollHeight > answer.clientHeight + 1) {
    const more = document.createElement("button");
    more.type = "button";
    more.className = "more-btn";
    more.textContent = status.show;
    more.setAttribute("aria-expanded", "false");
    more.addEventListener("click", () => {
      const open = answer.classList.toggle("clamped") === false;
      more.textContent = open ? status.less : status.show;
      more.setAttribute("aria-expanded", String(open));
      if (!open) more.scrollIntoView({ block: "nearest" }); // don't leave the reader far below
    });
    box.append(more);
  }
  box.parentElement.querySelector(".count").textContent =
    `${countWords(text).toLocaleString()} ${status.words}`;
}

async function loadAnswers() {
  try {
    const saved = JSON.parse(await fetchText(DEMO + "saved_answers.json"));
    document.querySelectorAll("#pairs .pair").forEach((li, i) => {
      for (const box of li.querySelectorAll(".answer")) {
        showAnswer(box, saved.pairs[i][box.dataset.side]);
      }
    });
  } catch (err) {
    $("answers-status").textContent = $("answers-status").dataset.failed;
    console.error(err);
  }
}

// Put playground.py (and llm.py, which it imports) into Pyodide's in-browser
// file system. llm.py is only used for --key mode, which the web never runs.
async function loadPython() {
  const py = await loadPyodide({ indexURL: PYODIDE_URL });
  py.FS.mkdirTree("/demo");
  for (const name of ["llm.py", "playground.py"]) {
    py.FS.writeFile(`/demo/${name}`, await fetchText(DEMO + name));
  }
  py.runPython("import sys; sys.path.insert(0, '/demo'); import playground");
  return py.globals.get("playground");
}

// The 4 pairs are written into the page so they show instantly.
// Re-check each one against the real code, so the page can never quietly lie.
function checkPairs(pg) {
  const pairs = pg.PAIRS.toJs({ dict_converter: Object.fromEntries });
  const total = pg.CHECKS.length;
  let allOk = true;
  document.querySelectorAll("#pairs .pair").forEach((li, i) => {
    const p = pairs[i] || {};
    const [vague, improved] = [...li.querySelectorAll(".prompt")].map((c) => c.textContent);
    const changes = [...li.querySelectorAll(".changes li")].map((c) => c.textContent);
    const score = `${pg.score(vague)}/${total} → ${pg.score(improved)}/${total}`;
    const ok = vague === p.vague && improved === p.improved &&
      JSON.stringify(changes) === JSON.stringify((p.changes || []).map(([n, w]) => `${n}: ${w}`)) &&
      li.querySelector(".score").textContent === score;
    if (!ok) {
      allOk = false;
      li.classList.add("ex-stale");
      li.querySelector(".ex-what").prepend("⚠ ");
    }
  });
  const live = $("checks-live");
  live.textContent = allOk ? live.dataset.ok : live.dataset.bad;
}

function checkOwn(pg) {
  const text = $("try").value.trim();
  const scoreEl = $("check-score");
  const list = $("check-list");
  list.replaceChildren();
  if (!text) {
    scoreEl.textContent = "";
    return;
  }
  const result = pg.check_prompt(text);
  const rows = result.toJs();
  result.destroy();
  const passed = rows.filter(([, , ok]) => ok).length;
  scoreEl.textContent = `${scoreEl.dataset.label} ${passed}/${rows.length}`;
  for (const [name, tip, ok] of rows) {
    const li = document.createElement("li");
    li.className = ok ? "pass" : "fail";
    const head = document.createElement("b");
    head.textContent = `${ok ? "✓" : "✗"} ${name}`;
    li.append(head);
    if (!ok) li.append(` — ${list.dataset.tip} ${tip}`);
    list.append(li);
  }
}

async function main() {
  loadAnswers();
  const status = $("status");
  status.textContent = status.dataset.loading;
  let pg;
  try {
    pg = await loadPython();
  } catch (err) {
    status.textContent = status.dataset.failed;
    console.error(err);
    return;
  }
  status.textContent = "";
  checkPairs(pg);

  const box = $("try");
  box.disabled = false;
  box.addEventListener("input", () => checkOwn(pg));
  for (const chip of document.querySelectorAll("#chips .chip-btn")) {
    chip.disabled = false;
    chip.addEventListener("click", () => {
      box.value = chip.dataset.try;
      checkOwn(pg);
      box.focus();
    });
  }
}

main();
