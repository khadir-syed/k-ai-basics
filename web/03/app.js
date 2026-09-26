// Runs Demo 03's real Python file (03-agent-trace/trace.py) inside the
// browser with Pyodide, in its rule-based mode. Nothing is sent anywhere: the
// page only downloads Pyodide and this repo's own files. It never talks to
// an AI. All page text is in index.html.
"use strict";

const DEMO = "../../03-agent-trace/";
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";
const $ = (id) => document.getElementById(id);

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.text();
}

// Put trace.py into Pyodide's in-browser file system. It's put first on the
// path, so it wins over Python's own module that is also called "trace".
async function loadPython() {
  const py = await loadPyodide({ indexURL: PYODIDE_URL });
  py.FS.mkdirTree("/demo");
  py.FS.writeFile("/demo/trace.py", await fetchText(DEMO + "trace.py"));
  py.runPython("import sys; sys.path.insert(0, '/demo'); import trace");
  return py;
}

// Run the agent on one question and collect the steps it prints.
function makeAgent(py) {
  const run = py.globals.get("trace").run_rule_based;
  return (question) => {
    const lines = [];
    py.setStdout({ batched: (line) => lines.push(line) });
    run(question);
    return lines.join("\n");
  };
}

// Show the steps safely (textContent only), with the [TAGS] in colour.
function render(pre, text) {
  pre.replaceChildren();
  for (const line of text.split("\n")) {
    const [, tag, rest] = line.match(/^(\[[A-Z ]+\])?(.*)$/);
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
function checkExamples(agent) {
  let allOk = true;
  for (const ex of document.querySelectorAll("#examples .ex")) {
    const question = ex.querySelector(".ex-in").textContent;
    const shown = ex.querySelector(".ex-trace").textContent;
    if (agent(question) !== shown) {
      allOk = false;
      ex.classList.add("ex-stale");
      ex.querySelector(".ex-why").prepend("⚠ ");
    }
  }
  const live = $("examples-live");
  live.textContent = allOk ? live.dataset.ok : live.dataset.bad;
}

function tryOwn(agent) {
  const question = $("try").value.trim();
  if (!question) $("try-output").replaceChildren();
  else render($("try-output"), agent(question));
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
  const agent = makeAgent(py);
  checkExamples(agent);

  const box = $("try");
  box.disabled = false;
  box.addEventListener("input", () => tryOwn(agent));
  for (const chip of document.querySelectorAll("#chips .chip-btn")) {
    chip.disabled = false;
    chip.addEventListener("click", () => {
      box.value = chip.dataset.try;
      tryOwn(agent);
      box.focus();
    });
  }
}

main();
