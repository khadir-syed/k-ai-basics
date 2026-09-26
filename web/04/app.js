// Runs Demo 04's real Python file (04-router-playground/router.py) inside the
// browser with Pyodide, in its rule-based mode. Nothing is sent anywhere: the
// page only downloads Pyodide and this repo's own files. It never talks to
// an AI. All page text is in index.html.
"use strict";

const DEMO = "../../04-router-playground/";
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";
const $ = (id) => document.getElementById(id);

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.text();
}

// Put router.py (and llm.py, which it imports) into Pyodide's in-browser file
// system. llm.py is only used for --key mode, which the web never runs.
async function loadPython() {
  const py = await loadPyodide({ indexURL: PYODIDE_URL });
  py.FS.mkdirTree("/demo");
  for (const name of ["llm.py", "router.py"]) {
    py.FS.writeFile(`/demo/${name}`, await fetchText(DEMO + name));
  }
  py.runPython("import sys; sys.path.insert(0, '/demo'); import router");
  return py;
}

// Route one request and collect the lines it prints.
function makeRouter(py) {
  const run = py.globals.get("router").run_rule_based;
  return (request) => {
    const lines = [];
    py.setStdout({ batched: (line) => lines.push(line) });
    run(request);
    return lines.join("\n");
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

// The 6 examples are written into the page so they show instantly.
// Re-run each one through the real code, so the page can never quietly lie.
function checkExamples(route) {
  let allOk = true;
  for (const ex of document.querySelectorAll("#examples .ex")) {
    const request = ex.querySelector(".ex-in").textContent;
    if (route(request) !== ex.querySelector(".ex-trace").textContent) {
      allOk = false;
      ex.classList.add("ex-stale");
      ex.querySelector(".ex-why").prepend("⚠ ");
    }
  }
  const live = $("examples-live");
  live.textContent = allOk ? live.dataset.ok : live.dataset.bad;
}

function tryOwn(route) {
  const request = $("try").value.trim();
  if (!request) $("try-output").replaceChildren();
  else render($("try-output"), route(request));
}

async function main() {
  const status = $("status");
  status.textContent = status.dataset.loading;
  let py;
  try {
    py = await loadPython();
  } catch (err) {
    status.textContent = status.dataset.failed;
    console.error(err);
    return;
  }
  status.textContent = "";
  const route = makeRouter(py);
  checkExamples(route);

  const box = $("try");
  box.disabled = false;
  box.addEventListener("input", () => tryOwn(route));
  for (const chip of document.querySelectorAll("#chips .chip-btn")) {
    chip.disabled = false;
    chip.addEventListener("click", () => {
      box.value = chip.dataset.try;
      tryOwn(route);
      box.focus();
    });
  }
}

main();
