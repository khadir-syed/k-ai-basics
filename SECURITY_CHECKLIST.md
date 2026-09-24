# Pre-Publish Security Checklist

Run through this before every commit pushed to this repo. Every commit
must pass all seven before it goes in:

- [x] **Architecture all good?** — each demo stays a small, self-contained folder with its own `requirements.txt`; no shared code between demos except the identical `llm.py` copies; no network calls or side effects outside the optional `--key` mode.
- [x] **Security all good?** — see [Secrets & Credentials](#secrets--credentials) and [Dependencies](#dependencies) below.
- [x] **Code standard wise all good?** — matches this repo's style (hand-rolled logic, no unneeded dependencies or frameworks, small self-contained demo folders), and runs without errors. If any `llm.py` changed, `python check_llm_copies.py` passes.
- [x] **Technically all good?** — the demo's `test_*.py` self-check passes, default mode gives the same output for the same input, and `--key` mode fails with a clear, non-crashing message when no key is set.
- [x] **No other tech issues?** — tested end-to-end by actually running the demo, not just reading the code.
- [x] **Documentation is up to date, along with required diagrams** — the relevant README(s) describe what the code does right now (not a planned future state), and any Mermaid diagram still matches the real flow.
- [x] **The rest of this checklist passes** — every section below, including [Commit Hygiene](#commit-hygiene).

## Secrets & Credentials
- [x] No API keys, tokens, or passwords committed (`gitleaks`/`git-secrets` not installed locally — ran an equivalent manual scan of the commit diff for key/token patterns each time; only match found was the placeholder `your-key-here` in READMEs)
- [x] No hardcoded cloud account IDs, internal hostnames, or employer-identifying data
- [x] `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` are only ever read from environment variables, never written to a file or printed

## Dependencies
- [x] `pip-audit` (or equivalent) run with no unresolved high/critical findings
- [x] Versions pinned in each demo's `requirements.txt`

## Data
- [x] Sample/bundled data (e.g. `02-mini-rag/docs/`) contains no real PII, no scraped personal data

## Repo Hygiene
- [x] LICENSE present
- [x] Each demo folder's README states clearly whether it needs an API key
- [x] Documentation matches what the code actually does — no README describing a feature that isn't built yet without saying so