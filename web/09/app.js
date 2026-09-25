// Runs Demo 09's real Python file (09-pii-redaction/redact.py) inside the
// browser with Pyodide. Nothing is sent anywhere: the page only downloads
// Pyodide and this repo's own files. All page text is in index.html.
"use strict";

const DEMO = "../../09-pii-redaction/";
const PYODIDE_URL = "https://cdn.jsdelivr.net/npm/pyodide@314.0.7/";
const $ = (id) => document.getElementById(id);

async function fetchText(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.text();
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

function makeRedact(py) {
  const fn = py.globals.get("redact").redact;
  return (text) => {
    const result = fn(text);
    const [redacted, counts] = result.toJs({ dict_converter: Object.fromEntries });
    result.destroy();
    return { redacted, counts };
  };
}

// The 6 examples are written into the page so they show instantly.
// Re-run each one through the real code, so the page can never quietly lie.
function checkExamples(redact) {
  let allOk = true;
  for (const ex of document.querySelectorAll("#examples .ex")) {
    const input = ex.querySelector(".ex-in").textContent;
    const shown = ex.querySelector(".ex-out").textContent;
    if (redact(input).redacted !== shown) {
      allOk = false;
      ex.classList.add("ex-stale");
      ex.querySelector(".ex-why").prepend("⚠ ");
    }
  }
  const live = $("examples-live");
  live.textContent = allOk ? live.dataset.ok : live.dataset.bad;
}

function runDemo(py) {
  const lines = [];
  py.setStdout({ batched: (line) => lines.push(line) });
  py.runPython("redact.run()");
  render($("output"), lines.join("\n"));
  $("legend").hidden = false;
  $("explain").hidden = false;
  $("run").textContent = $("run").dataset.again;
}

function tryOwn(redact) {
  const text = $("try").value;
  const found = $("try-found");
  if (!text.trim()) {
    $("try-output").replaceChildren();
    found.textContent = "";
    return;
  }
  const { redacted, counts } = redact(text);
  const hits = Object.entries(counts).filter(([, n]) => n).map(([k, n]) => `${k} (${n})`);
  found.textContent = `${found.dataset.label} ${hits.join(", ") || found.dataset.none}`;
  render($("try-output"), redacted);
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
  const redact = makeRedact(py);
  checkExamples(redact);

  const run = $("run");
  run.disabled = false;
  run.addEventListener("click", () => runDemo(py));

  const box = $("try");
  box.disabled = false;
  box.addEventListener("input", () => tryOwn(redact));
  for (const chip of document.querySelectorAll("#chips .chip-btn")) {
    chip.disabled = false;
    chip.addEventListener("click", () => {
      box.value = chip.dataset.try;
      tryOwn(redact);
      box.focus();
    });
  }
}

main();
