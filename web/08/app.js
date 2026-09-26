// Runs Demo 08's real Python file (08-prompt-injection/inject.py) inside the
// browser with Pyodide, with its rule-based mock agent. Nothing is sent
// anywhere: the page only downloads Pyodide and this repo's own files. It
// never talks to an AI. All page text is in index.html.
"use strict";

const DEMO = "../../08-prompt-injection/";
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";
const DOCS = ["1_ticket_clean.txt", "2_ticket_injected.txt", "3_webpage_reworded.txt"];
const YOURS = "your_document.txt";
const $ = (id) => document.getElementById(id);

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.text();
}

// Put inject.py (and llm.py, which it imports) and the 3 documents into
// Pyodide's in-browser file system. llm.py is only used for --key mode,
// which the web never runs.
async function loadPython() {
  const py = await loadPyodide({ indexURL: PYODIDE_URL });
  py.FS.mkdirTree("/demo/docs");
  for (const name of ["llm.py", "inject.py"]) {
    py.FS.writeFile(`/demo/${name}`, await fetchText(DEMO + name));
  }
  const docs = {};
  for (const name of DOCS) {
    docs[name] = await fetchText(`${DEMO}docs/${name}`);
    py.FS.writeFile(`/demo/docs/${name}`, docs[name]);
  }
  py.runPython("import sys; sys.path.insert(0, '/demo'); import inject");
  return { py, docs };
}

// Send one document down one path (filter on or off) and collect the lines
// it prints. Your own text goes in as a file, just like the demo's documents.
function makeRun(py) {
  const inject = py.globals.get("inject");
  return (doc, useFilter, text) => {
    if (text !== undefined) py.FS.writeFile(`/demo/docs/${doc}`, text);
    const lines = [];
    py.setStdout({ batched: (line) => lines.push(line) });
    let failed = false;
    try {
      inject.run_path(doc, useFilter, inject.mock_agent);
    } catch (err) {
      failed = true; // e.g. the filter cut every sentence: nothing left to sum up
      console.error(err);
    }
    // Each step ends with a blank line in the terminal; the page doesn't need it.
    return { text: lines.join("\n").replace(/\n+$/, ""), failed };
  };
}

// Show the lines safely (textContent only), with the [TAGS] in colour.
function render(pre, text) {
  pre.replaceChildren();
  for (const line of text.split("\n")) {
    const [, tag, rest] = line.match(/^(\[[^\]]+\])?(.*)$/);
    if (tag) {
      const span = document.createElement("span");
      span.className = "tag";
      span.textContent = tag;
      pre.append(span);
    }
    pre.append(rest, "\n");
  }
}

// The 4 steps are written into the page so they show instantly.
// Re-run each one through the real code, so the page can never quietly lie.
function checkExamples(run) {
  let allOk = true;
  for (const ex of document.querySelectorAll("#examples .ex")) {
    const out = run(ex.dataset.doc, ex.dataset.filter === "on");
    if (out.failed || out.text !== ex.querySelector(".ex-trace").textContent) {
      allOk = false;
      ex.classList.add("ex-stale");
      ex.querySelector(".ex-why").prepend("⚠ ");
    }
  }
  const live = $("examples-live");
  live.textContent = allOk ? live.dataset.ok : live.dataset.bad;
}

function tryOwn(run) {
  const pre = $("try-output");
  const text = $("try").value.trim();
  if (!text) return pre.replaceChildren();
  const out = run(YOURS, $("filter").checked, text);
  render(pre, out.text);
  if (out.failed) pre.append(pre.dataset.error);
}

async function main() {
  const status = $("status");
  status.textContent = status.dataset.loading;
  let loaded;
  try {
    loaded = await loadPython();
  } catch (err) {
    status.textContent = status.dataset.failed;
    console.error(err);
    return;
  }
  status.textContent = "";
  const run = makeRun(loaded.py);
  checkExamples(run);

  const box = $("try");
  box.disabled = false;
  box.addEventListener("input", () => tryOwn(run));
  $("filter").disabled = false;
  $("filter").addEventListener("change", () => tryOwn(run));
  for (const chip of document.querySelectorAll("#chips .chip-btn")) {
    chip.disabled = false;
    chip.addEventListener("click", () => {
      box.value = loaded.docs[chip.dataset.doc];
      tryOwn(run);
      box.focus();
    });
  }
}

main();
