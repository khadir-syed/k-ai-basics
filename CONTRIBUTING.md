# Contributing

Thanks for your interest in contributing. This repository is a small
collection of beginner-facing demos that show how core AI concepts work,
one idea at a time, in a terminal — and, for some demos, in the browser
via the static pages in [`web/`](web/README.md). Contributions should keep
that goal in mind: no heavyweight frameworks, no servers or paid hosting
(only the static GitHub Pages site), and a default path that runs with
zero API key and zero config.

## Before you open a pull request

- Read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) — participation in this
  project means agreeing to it.
- Search existing issues and pull requests to avoid duplicating work.
- For a change larger than a typo or wording fix, open an issue first to
  discuss the approach before writing it up.

## Adding a new demo

Each demo lives in its own numbered top-level folder (`01-tokenizer-playground`,
`02-mini-rag`, `03-agent-trace`, and so on), fully self-contained — its own
`requirements.txt`, its own `README.md`, nothing shared with other demos.
Someone should be able to copy a single demo folder out of this repo and
have it still work.

```text
0N-demo-name/
├── README.md
├── requirements.txt
├── <entry-point>.py
├── test_<entry-point>.py
└── llm.py              (only if the demo has a --key mode — see rule 1)
```

A new demo should:

1. **Run with zero API key and zero config by default.** If the concept
   benefits from a real LLM call, gate that behind an explicit `--key` flag
   that reads `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` from an environment
   variable only — never a file, never printed, never hardcoded.
   For a simple "send a prompt, get text back" call, copy `llm.py` from
   an existing demo (e.g. `02-mini-rag/llm.py`) into your folder, unchanged.
   Every demo keeps its own copy so the folder still works on its own, and
   `python check_llm_copies.py` (repo root) fails if the copies ever differ.
2. **Avoid heavyweight frameworks.** Prefer the standard library or one or
   two small, well-known packages (e.g. `transformers`, `scikit-learn`)
   over agent/orchestration frameworks. The point is to show the mechanism,
   not to hide it behind abstraction.
3. **Explain itself like the reader is five years old.** The README should
   use a plain-English analogy before any technical explanation, and every
   run step should be spelled out (open terminal, make a venv, install,
   run, what the output means). Use only relative paths in commands — never
   a local machine's absolute folder names.
4. **Include a Mermaid diagram if it genuinely adds clarity** for a
   beginner — a picture of the pipeline (input → step → step → output) —
   but skip it if the flow is trivially linear and a diagram would just
   restate the text.
5. **Leave one runnable self-check behind** (`test_<entry-point>.py`,
   plain `assert`-based, no test framework) that exercises the demo's
   real logic — chunking, routing, scoring, whatever the core mechanism
   is — and fails if that logic breaks. It should run instantly with no
   network access or model download required.
6. **State clearly whether it needs an API key**, in its own README and in
   the demo table in the root [README.md](README.md).

## Improving an existing demo

- Keep changes scoped to one concern per pull request.
- Do not weaken the "no API key needed by default" guarantee or silently
  add a new required dependency to make a change "more convenient."
- If you change what the demo actually does, update its README (and any
  Mermaid diagram) in the same pull request — this repo does not allow
  documentation to describe a future or past state of the code.

## Testing your change

There is no build step or CI. "Testing" a demo change means:

1. Actually running the demo end-to-end from a clean virtual environment,
   not just reading the code.
2. Running its `test_*.py` self-check and confirming it passes.
3. If the demo has an optional `--key` path, confirming it fails with a
   clear, non-crashing message when no key is set.
4. Running `pip-audit` (or equivalent) against the demo's `requirements.txt`
   with no unresolved high/critical findings.

## Pull request checklist

This mirrors [SECURITY_CHECKLIST.md](SECURITY_CHECKLIST.md), which every
commit in this repo is expected to pass:

- [ ] No API keys, tokens, or passwords committed anywhere in the diff.
- [ ] `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, if used, are read from
      environment variables only.
- [ ] Dependencies are pinned in the demo's `requirements.txt`, and
      `pip-audit` (or equivalent) has been run with no unresolved
      high/critical findings.
- [ ] The demo runs end-to-end without errors, and its `test_*.py`
      self-check passes.
- [ ] If any `llm.py` was touched, `python check_llm_copies.py` passes
      (every copy identical).
- [ ] The demo's README (and any diagram) matches exactly what the code
      does right now — no describing an unbuilt feature without saying so.
- [ ] Root [README.md](README.md) demo table updated if a demo was added,
      renamed, or removed.

## Reporting a security issue

If you find a security concern (not a general bug), please open an issue
and describe it — this repository has no runtime service, no server, and
no user data, so most reports can be handled in the open, but flag
anything sensitive so it can be triaged appropriately.
