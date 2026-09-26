// Runs Demo 06's real Python file (06-hallucination-demo/compare.py) inside
// the browser with Pyodide: the "look it up first" side. compare.py needs
// scikit-learn, which makes the download big, so nothing loads until the
// visitor taps "Load". The AI answers on this page were saved from a real
// run; the page itself never talks to an AI. All page text is in index.html.
"use strict";

const DEMO = "../../06-hallucination-demo/";
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";
// scikit-learn isn't in Pyodide's npm files, only in its full set, same version.
const PACKAGES_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
const $ = (id) => document.getElementById(id);

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.text();
}

// The page lists the 3 Puddlewick files; their titles come from the same list.
const docs = () =>
  Object.fromEntries([...document.querySelectorAll("#docs li")].map((li) => [li.dataset.file, li.textContent]));

// Put compare.py (and llm.py, which it imports) and the Puddlewick files into
// Pyodide's in-browser file system. llm.py is only used for --key mode, which
// the web never runs.
async function loadPython() {
  const py = await loadPyodide({ indexURL: PYODIDE_URL, packageBaseUrl: PACKAGES_URL });
  await py.loadPackage("scikit-learn");
  py.runPython("import sklearn"); // loadPackage only logs a failed download; this makes it stop here
  py.FS.mkdirTree("/demo/docs");
  for (const name of ["llm.py", "compare.py"]) {
    py.FS.writeFile(`/demo/${name}`, await fetchText(DEMO + name));
  }
  for (const name of Object.keys(docs())) {
    py.FS.writeFile(`/demo/docs/${name}`, await fetchText(`${DEMO}docs/${name}`));
  }
  py.runPython("import sys; sys.path.insert(0, '/demo'); import compare; chunks = compare.load_chunks()");
  return py;
}

// Rank the paragraphs with the demo's own rank_chunks() (its top 3), and mark
// which ones clear its THRESHOLD — the line between evidence and a guess.
function makeSearch(py) {
  const compare = py.globals.get("compare");
  const chunks = py.globals.get("chunks");
  const threshold = compare.THRESHOLD;
  return (question) => {
    const result = compare.rank_chunks(question, chunks);
    const rows = result.toJs();
    result.destroy();
    return rows.map(([file, text, score]) => ({ file, text, score, strong: score >= threshold }));
  };
}

const pct = (score) => `${(score * 100).toFixed(1)}%`;

// The 6 examples are written into the page so they show instantly.
// Re-run each lookup through the real code, so the page can never quietly lie.
function checkExamples(search) {
  let allOk = true;
  for (const ex of document.querySelectorAll("#examples .ex")) {
    const best = search(ex.querySelector(".ex-in").textContent)[0];
    const found = ex.querySelector(".found");
    const ok = best.strong
      ? found.dataset.file === best.file &&
        found.querySelector(".found-text").textContent === best.text &&
        found.querySelector(".found-pct").textContent === pct(best.score)
      : found.dataset.file === "";
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

// Show the top 3 like the terminal does — file, score bar, %, ✓ or ✗ — then the
// best evidence, or the honest "I don't know". Text only, never HTML.
function showResults(search) {
  const box = $("results");
  const question = $("try").value.trim();
  box.replaceChildren();
  if (!question) return;
  const results = search(question);
  const text = box.dataset;
  const titles = docs();
  if (results[0].score === 0) {
    box.append(el("p", "found-text none", text.nothing));
  } else {
    const list = el("ol", "matches");
    for (const { file, text: para, score, strong } of results) {
      const row = el("li", "match");
      const bar = el("span", "bar");
      bar.style.width = `${score * 100}%`;
      const track = el("span", "bar-track");
      track.append(bar);
      row.append(
        el("span", "match-story", titles[file] || file),
        el("span", "match-pct", `${pct(score)} ${strong ? text.strong : text.weak}`),
        track,
        el("span", "match-text", para.length <= 70 ? para : `${para.slice(0, 67)}...`),
      );
      list.append(row);
    }
    box.append(el("p", "try-label", text.top), list);
  }
  const best = results[0];
  if (!best.strong) {
    box.append(el("p", "found-text none", text.dontknow));
    return;
  }
  const found = el("div", "found");
  found.append(el("p", "found-story", `${titles[best.file]} · ${pct(best.score)}`), el("p", "found-text", best.text));
  box.append(el("p", "try-label", text.best), found, el("p", "muted", text.check));
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
