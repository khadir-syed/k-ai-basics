# Pre-Publish Security Checklist

Run through this before every commit pushed to this repo. Every commit
must pass all four before it goes in:

- [x] **Security all good?** — see [Secrets & Credentials](#secrets--credentials) and [Dependencies](#dependencies) below.
- [x] **Code standard wise all good?** — matches this repo's style (hand-rolled logic, no unneeded dependencies or frameworks, small self-contained demo folders), and runs without errors.
- [x] **No other tech issues?** — tested end-to-end by actually running the demo, not just reading the code.
- [x] **Documentation is up to date, along with required diagrams** — the relevant README(s) describe what the code does right now (not a planned future state), and any Mermaid diagram still matches the real flow.

## Secrets & Credentials
- [x] No API keys, tokens, or passwords committed (`gitleaks`/`git-secrets` not installed locally — ran an equivalent manual scan of the commit diff for key/token patterns; only match was the placeholder `your-key-here` in the README)
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
