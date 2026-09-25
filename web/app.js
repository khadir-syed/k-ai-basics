// Runs Demo 09's real Python file (09-pii-redaction/redact.py) inside the
// browser with Pyodide. Nothing is sent anywhere: the page only downloads
// Pyodide and this repo's own files.
"use strict";

const DEMO = "../09-pii-redaction/";
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";
const $ = (id) => document.getElementById(id);
let T = {};
let redactFn = null;

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.text();
}

// Fill every [data-t] element with its sentence from strings.<lang>.json.
async function loadStrings(lang) {
  T = JSON.parse(await fetchText(`strings.${lang}.json`));
  document.documentElement.lang = T.lang;
  document.title = T.page_title;
  document.querySelectorAll("[data-t]").forEach((el) => { el.textContent = T[el.dataset.t]; });
  $("try").placeholder = T.try_placeholder;
}

// Put redact.py and its docs/ into Pyodide's in-browser file system.
async function loadPython() {
  const py = await loadPyodide({ indexURL: PYODIDE_URL });
  py.FS.mkdirTree("/demo/docs");
  py.FS.writeFile("/demo/redact.py", await fetchText(DEMO + "redact.py"));
  const key = await fetchText(DEMO + "docs/answer_key.json");
  py.FS.writeFile("/demo/docs/answer_key.json", key);
  const docs = Object.keys(JSON.parse(key)).filter((k) => !k.startsWith("_"));
  for (const name of docs) {
    py.FS.writeFile(`/demo/docs/${name}`, await fetchText(`${DEMO}docs/${name}`));
  }
  py.runPython("import sys; sys.path.insert(0, '/demo'); import redact");
  return py;
}

// Show text safely (textContent only) with colour for tags, labels and misses.
function render(pre, text) {
  pre.replaceChildren();
  for (const line of text.split("\n")) {
    const row = document.createElement("span");
    if (line.startsWith("[MISSED]")) row.className = "missed-line";
    if (/^\[(CAUGHT|LESSON)\]/.test(line)) row.className = "summary";
    if (line.startsWith("──")) row.className = "rule";
    for (const part of line.split(/(\[REDACTED-[A-Z]+\]|^\[[A-Z]+\])/)) {
      if (!part) continue;
      const span = document.createElement("span");
      if (/^\[REDACTED-/.test(part)) span.className = "redacted";
      else if (/^\[[A-Z]+\]$/.test(part) && part !== "[MISSED]") span.className = "tag";
      span.textContent = part;
      row.appendChild(span);
    }
    pre.append(row, "\n");
  }
  pre.hidden = false;
}

function runDemo(py) {
  const lines = [];
  py.setStdout({ batched: (line) => lines.push(line) });
  py.runPython("redact.run()");
  render($("output"), lines.join("\n"));
  $("legend").hidden = false;
  $("explain").hidden = false;
  $("run").textContent = T.run_again;
}

function tryOwn() {
  const text = $("try").value;
  if (!text.trim()) {
    $("try-output").replaceChildren();
    $("try-found").textContent = "";
    return;
  }
  const result = redactFn(text);
  const [redacted, counts] = result.toJs({ dict_converter: Object.fromEntries });
  result.destroy();
  const found = Object.entries(counts).filter(([, n]) => n).map(([k, n]) => `${k} (${n})`);
  $("try-found").textContent = `${T.try_found} ${found.join(", ") || T.try_none}`;
  render($("try-output"), redacted);
}

async function main() {
  await loadStrings("en");
  const run = $("run");
  run.disabled = true;
  $("status").textContent = T.loading;
  let py;
  try {
    py = await loadPython();
  } catch (err) {
    $("status").textContent = T.load_failed;
    console.error(err);
    return;
  }
  $("status").textContent = "";
  run.disabled = false;
  run.addEventListener("click", () => runDemo(py));
  redactFn = py.globals.get("redact").redact;
  const box = $("try");
  box.disabled = false;
  box.value = T.try_example;
  box.addEventListener("input", tryOwn);
  tryOwn();
}

main();
