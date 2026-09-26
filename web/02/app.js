// Runs Demo 02's real Python file (02-mini-rag/ask.py) inside the browser
// with Pyodide. ask.py needs scikit-learn, which makes the download big, so
// nothing loads until the visitor taps "Load". Nothing is sent anywhere: the
// page only downloads Pyodide (and its scikit-learn) and this repo's own
// files. It never talks to an AI. All page text is in index.html.
"use strict";

const DEMO = "../../02-mini-rag/";
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";
// scikit-learn isn't in Pyodide's npm files, only in its full set, same version.
const PACKAGES_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
const $ = (id) => document.getElementById(id);

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.text();
}

// The page lists the 4 story files; their titles come from the same list.
const stories = () =>
  Object.fromEntries([...document.querySelectorAll("#stories li")].map((li) => [li.dataset.file, li.textContent]));

// Put ask.py (and llm.py, which it imports) and the stories into Pyodide's
// in-browser file system. llm.py is only used for --key mode, which the web
// never runs.
async function loadPython() {
  const py = await loadPyodide({ indexURL: PYODIDE_URL, packageBaseUrl: PACKAGES_URL });
  await py.loadPackage("scikit-learn");
  py.runPython("import sklearn"); // loadPackage only logs a failed download; this makes it stop here
  py.FS.mkdirTree("/demo/docs");
  for (const name of ["llm.py", "ask.py"]) {
    py.FS.writeFile(`/demo/${name}`, await fetchText(DEMO + name));
  }
  for (const name of Object.keys(stories())) {
    py.FS.writeFile(`/demo/docs/${name}`, await fetchText(`${DEMO}docs/${name}`));
  }
  py.runPython("import sys; sys.path.insert(0, '/demo'); import ask; chunks = ask.load_chunks()");
  return py;
}

// Rank every paragraph against a question with the demo's own rank_chunks().
function makeSearch(py) {
  const rank = py.globals.get("ask").rank_chunks;
  const chunks = py.globals.get("chunks");
  return (question) => {
    const result = rank(question, chunks);
    const rows = result.toJs();
    result.destroy();
    return rows.map(([file, text, score]) => ({ file, text, score }));
  };
}

// The 6 examples are written into the page so they show instantly.
// Re-run each one through the real code, so the page can never quietly lie.
function checkExamples(search) {
  let allOk = true;
  for (const ex of document.querySelectorAll("#examples .ex")) {
    const best = search(ex.querySelector(".ex-in").textContent)[0];
    const found = ex.querySelector(".found");
    const ok = best.score === 0
      ? found.dataset.file === ""
      : found.dataset.file === best.file && found.querySelector(".found-text").textContent === best.text;
    if (!ok) {
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

// Show the top 5 like the terminal does: story, score bar, % and the start of
// each paragraph — then the best paragraph in full. Text only, never HTML.
function showResults(search) {
  const box = $("results");
  const question = $("try").value.trim();
  box.replaceChildren();
  if (!question) return;
  const results = search(question);
  const text = box.dataset;
  // Same rule as ask.py: a top score of 0 means no word was shared at all.
  if (results[0].score === 0) {
    box.append(el("p", "found-text none", text.none));
    return;
  }
  const titles = stories();
  const list = el("ol", "matches");
  for (const { file, text: para, score } of results) {
    const row = el("li", "match");
    const bar = el("span", "bar");
    bar.style.width = `${score * 100}%`;
    const track = el("span", "bar-track");
    track.append(bar);
    row.append(
      el("span", "match-story", titles[file] || file),
      el("span", "match-pct", `${(score * 100).toFixed(1)}%`),
      track,
      el("span", "match-text", para.length <= 70 ? para : `${para.slice(0, 67)}...`),
    );
    list.append(row);
  }
  const best = el("div", "found");
  best.append(el("p", "found-story", titles[results[0].file]), el("p", "found-text", results[0].text));
  box.append(el("p", "try-label", text.top), list, el("p", "try-label", text.best), best);
}

async function start() {
  const load = $("load");
  const status = $("status");
  load.disabled = true;
  status.textContent = status.dataset.loading;
  let py;
  try {
    py = await loadPython();
  } catch (err) {
    status.textContent = status.dataset.failed;
    load.disabled = false;
    console.error(err);
    return;
  }
  status.textContent = "";
  load.hidden = true;
  const search = makeSearch(py);
  checkExamples(search);

  $("try-area").hidden = false;
  const box = $("try");
  box.addEventListener("input", () => showResults(search));
  for (const chip of document.querySelectorAll("#chips .chip-btn")) {
    chip.addEventListener("click", () => {
      box.value = chip.dataset.try;
      showResults(search);
      box.focus();
    });
  }
}

const load = $("load");
load.disabled = false;
load.addEventListener("click", start);
