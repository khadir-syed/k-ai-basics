// Runs Demo 10's real Python file (10-multi-agent-handoff/handoff.py) inside
// the browser with Pyodide, in its rule-based mode. Nothing is sent anywhere:
// the page only downloads Pyodide and this repo's own files. It never talks
// to an AI. All page text is in index.html.
"use strict";

const DEMO = "../../10-multi-agent-handoff/";
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";
const $ = (id) => document.getElementById(id);

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.text();
}

// Put handoff.py (and llm.py, which it imports) into Pyodide's in-browser file
// system. llm.py is only used for --key mode, which the web never runs.
async function loadPython() {
  const py = await loadPyodide({ indexURL: PYODIDE_URL });
  py.FS.mkdirTree("/demo");
  for (const name of ["llm.py", "handoff.py"]) {
    py.FS.writeFile(`/demo/${name}`, await fetchText(DEMO + name));
  }
  py.runPython("import sys; sys.path.insert(0, '/demo'); import handoff");
  return py;
}

// Run both agents on one bug report and collect the lines they print.
function makeTeam(py) {
  const run = py.globals.get("handoff").run;
  return (report, handoff) => {
    const lines = [];
    py.setStdout({ batched: (line) => lines.push(line) });
    run(report, handoff);
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
function checkExamples(team) {
  let allOk = true;
  for (const ex of document.querySelectorAll("#examples .ex")) {
    const report = ex.querySelector(".ex-in").textContent;
    if (team(report, ex.dataset.handoff) !== ex.querySelector(".ex-trace").textContent) {
      allOk = false;
      ex.classList.add("ex-stale");
      ex.querySelector(".ex-why").prepend("⚠ ");
    }
  }
  const live = $("examples-live");
  live.textContent = allOk ? live.dataset.ok : live.dataset.bad;
}

// The real AI's reply is saved in the page. Run the demo's own JSON check on
// it, so "passed" is never just our word for it.
function checkRealRun(py) {
  const result = py.globals.get("handoff").check_json($("real-draft").textContent);
  const [, problem] = result.toJs(); // (draft, None) when the form is fine
  result.destroy();
  const line = $("real-check");
  line.textContent = problem == null ? line.dataset.ok : line.dataset.bad;
}

function tryOwn(team) {
  const report = $("try").value.trim();
  const handoff = document.querySelector('#handoff input:checked').value;
  if (!report) $("try-output").replaceChildren();
  else render($("try-output"), team(report, handoff));
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
  const team = makeTeam(py);
  checkExamples(team);
  checkRealRun(py);

  const box = $("try");
  box.disabled = false;
  box.addEventListener("input", () => tryOwn(team));
  for (const radio of document.querySelectorAll("#handoff input")) {
    radio.disabled = false;
    radio.addEventListener("change", () => tryOwn(team));
  }
  for (const chip of document.querySelectorAll("#chips .chip-btn")) {
    chip.disabled = false;
    chip.addEventListener("click", () => {
      box.value = chip.dataset.try;
      tryOwn(team);
      box.focus();
    });
  }
}

main();
