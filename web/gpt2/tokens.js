// Shared by Demos 01 and 05: load GPT-2's tokenizer (gpt2.py, built with
// tiktoken from the word lists next to it), and draw its tokens on the page.
"use strict";

// tiktoken isn't in Pyodide's npm files, only in its full set, same version.
const GPT2_PACKAGES_URL = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";

// Put gpt2.py and its word lists into Pyodide, and return pieces(text):
// [{ letter, tokens: [{ piece, id }] }] — see Tokenizer.pieces in gpt2.py.
async function loadGpt2(py, fetchText) {
  await py.loadPackage("tiktoken");
  py.runPython("import tiktoken"); // loadPackage only logs a failed download; this makes it stop here
  py.FS.mkdirTree("/gpt2");
  for (const name of ["gpt2.py", "vocab.json", "merges.txt"]) {
    py.FS.writeFile(`/gpt2/${name}`, await fetchText(`../gpt2/${name}`));
  }
  py.runPython('import sys; sys.path.insert(0, "/gpt2"); import gpt2; _gpt2 = gpt2.Tokenizer()');
  const tokenizer = py.globals.get("_gpt2");
  return (text) => {
    const result = tokenizer.pieces(text);
    const groups = result.toJs();
    result.destroy();
    return groups.map(([letter, tokens]) => ({
      letter: letter ?? null,
      tokens: tokens.map(([piece, id]) => ({ piece, id })),
    }));
  };
}

// Spaces and line breaks are hard to see, so they're shown as · and ↵.
const showPiece = (text) => text.replaceAll(" ", "·").replaceAll("\n", "↵");

function tokenItem({ piece, id }) {
  const li = document.createElement("li");
  li.dataset.id = id;
  const code = document.createElement("code");
  code.className = "tok";
  code.textContent = showPiece(piece);
  const num = document.createElement("span");
  num.className = "tok-id";
  num.textContent = id;
  li.append(code, num);
  return li;
}

// Draw tokens as little bricks with their ID numbers. Pieces of one letter
// sit together in a bracket, with the letter they make underneath.
function drawTokens(groups) {
  const list = document.createElement("ol");
  list.className = "tokens";
  for (const { letter, tokens } of groups) {
    if (letter === null) {
      list.append(...tokens.map(tokenItem));
      continue;
    }
    const group = document.createElement("li");
    group.className = "tok-group";
    const inner = document.createElement("ol");
    inner.className = "tokens";
    inner.append(...tokens.map(tokenItem));
    const label = document.createElement("span");
    label.className = "tok-letter";
    label.textContent = showPiece(letter);
    group.append(inner, label);
    list.append(group);
  }
  return list;
}

// Read tokens drawn in the page (by hand or by drawTokens) back into groups,
// so a page can check the tokens it shows against the real tokenizer.
function readTokens(list) {
  return [...list.children].flatMap((li) => {
    const item = (t) => ({ piece: t.querySelector(".tok").textContent, id: Number(t.dataset.id) });
    if (!li.classList.contains("tok-group")) return [{ letter: null, tokens: [item(li)] }];
    return [{ letter: li.querySelector(".tok-letter").textContent, tokens: [...li.querySelectorAll("li[data-id]")].map(item) }];
  });
}

// Do the drawn tokens say exactly what the tokenizer says? (Each whole token
// is compared on its own; a letter's pieces are compared as one group.)
function sameTokens(list, groups) {
  const flat = (gs) => gs.flatMap(({ letter, tokens }) =>
    (letter === null ? tokens.map((t) => ({ letter: null, tokens: [t] })) : [{ letter, tokens }]));
  const shown = groups.map(({ letter, tokens }) => ({
    letter: letter === null ? null : showPiece(letter),
    tokens: tokens.map(({ piece, id }) => ({ piece: showPiece(piece), id })),
  }));
  return JSON.stringify(flat(readTokens(list))) === JSON.stringify(flat(shown));
}

// Every token's ID number, in order: what the AI actually sees.
const tokenIds = (groups) => groups.flatMap(({ tokens }) => tokens.map((t) => t.id));
