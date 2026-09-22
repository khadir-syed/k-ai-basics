# Pre-Publish Security Checklist

Run through this before every commit pushed to this repo. Every commit
must pass all four before it goes in:

- [ ] **Security all good?** — see [Secrets & Credentials](#secrets--credentials) and [Dependencies](#dependencies) below.
- [ ] **Code standard wise all good?** — matches this repo's style (hand-rolled logic, no unneeded dependencies or frameworks, small self-contained demo folders), and runs without errors.
- [ ] **No other tech issues?** — tested end-to-end by actually running the demo, not just reading the code.
- [ ] **Documentation is up to date, along with required diagrams** — the relevant README(s) describe what the code does right now (not a planned future state), and any Mermaid diagram still matches the real flow.

## Secrets & Credentials
- [ ] No API keys, tokens, or passwords committed (run `gitleaks detect` or `git secrets --scan` before first push)
- [ ] No hardcoded cloud account IDs, internal hostnames, or employer-identifying data
- [ ] `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` are only ever read from environment variables, never written to a file or printed

## Dependencies
- [ ] `pip-audit` (or equivalent) run with no unresolved high/critical findings
- [ ] Versions pinned in each demo's `requirements.txt`

## Data
- [ ] Sample/bundled data (e.g. `02-mini-rag/docs/`) contains no real PII, no scraped personal data

## Repo Hygiene
- [ ] LICENSE present
- [ ] Each demo folder's README states clearly whether it needs an API key
- [ ] Documentation matches what the code actually does — no README describing a feature that isn't built yet without saying so
