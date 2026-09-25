# Pre-Publish Security Checklist

Run through this before every commit pushed to this repo. Every commit
must pass all seven before it goes in:

- [x] **Architecture all good?** — each demo stays a small, self-contained folder with its own `requirements.txt`; no shared code between demos except the identical `llm.py` copies; no network calls or side effects outside the optional `--key` mode.
- [x] **Security all good?** — see [Secrets & Credentials](#secrets--credentials) and [Dependencies](#dependencies) below.
- [x] **Code standard wise all good?** — matches this repo's style (hand-rolled logic, no unneeded dependencies or frameworks, small self-contained demo folders), and runs without errors. If any `llm.py` changed, `python check_llm_copies.py` passes.
- [x] **Technically all good?** — the demo's `test_*.py` self-check passes, default mode gives the same output for the same input, and `--key` mode fails with a clear, non-crashing message when no key is set.
- [x] **No other tech issues?** — tested end-to-end by actually running the demo, not just reading the code.
- [x] **Documentation is up to date, along with required diagrams** — the relevant README(s) describe what the code does right now (not a planned future state), and any Mermaid diagram still matches the real flow.
- [x] **The rest of this checklist passes** — every section below, including [Web pages](#web-pages-web) if anything in `web/` changed.

## Secrets & Credentials
- [x] No API keys, tokens, or passwords committed (`gitleaks`/`git-secrets` not installed locally — ran an equivalent manual scan of the commit diff for key/token patterns each time; only match found was the placeholder `your-key-here` in READMEs)
- [x] No hardcoded cloud account IDs, internal hostnames, or employer-identifying data
- [x] `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` are only ever read from environment variables, never written to a file or printed

## Dependencies
- [x] `pip-audit` finds no known vulnerabilities in any demo that installs packages (01, 02, 05, 06): in each of those folders, with its `.venv` switched on, run `pip install pip-audit` and then `pip-audit`. It checks every installed package, including the ones they pull in. Fix or explain any finding before pushing
- [x] Versions pinned in each demo's `requirements.txt`

## Data
- [x] Sample/bundled data (e.g. `02-mini-rag/docs/`) contains no real PII, no scraped personal data

## Web pages (`web/`)
- [ ] Pages load the demo's own unchanged `.py` file — no copied or rewritten demo logic
- [ ] Every page keeps its strict `Content-Security-Policy`: only its own files, the pinned Pyodide from jsDelivr, and the GitHub profile photo; no inline scripts
- [ ] Pyodide is pinned to one exact version, the same in every demo page's `index.html` and `app.js`, and the `integrity="sha384-…"` fingerprint matches that version (see [web/README.md](web/README.md#upgrading-pyodide-read-this-first))
- [ ] Text is shown with `textContent` only — no `innerHTML`, `eval`, or `document.write`
- [ ] No cookies, storage, analytics or tracking; nothing a visitor types is sent anywhere
- [ ] No `--key` mode and no API keys on the web
- [ ] Examples use only made-up data (IDs starting `000`, test card numbers, `example.com` emails), and `python web/test_web.py` passes
- [ ] The publishing workflow's actions are pinned to full commit codes, with least-privilege permissions
- [ ] Tested locally in a browser (desktop and phone width) before pushing, and checked on the live site after

## Repo Hygiene
- [x] LICENSE present
- [x] Each demo folder's README states clearly whether it needs an API key
- [x] Documentation matches what the code actually does — no README describing a feature that isn't built yet without saying so