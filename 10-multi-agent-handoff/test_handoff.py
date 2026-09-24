"""Self-check for both agents' rules and the JSON handoff check.
Runs instantly, no network. Run with: python test_handoff.py
"""
import json

from handoff import FIELDS, check_json, draft_rules, to_text, triage_rules

# Drafter: fills every field, leaves severity to Triage, spots devices and steps.
d = draft_rules("the app crashes when I upload big files")
assert list(d) == FIELDS
assert d["title"] == "The app crashes when I upload big files"
assert d["severity"] == "unknown" and d["steps"] == "not provided"
assert d["environment"] == "not provided"
d2 = draft_rules("Checkout is slow in Chrome. Steps: 1. add item 2. click pay")
assert d2["title"] == "Checkout is slow in Chrome." and d2["environment"] == "chrome"
assert d2["steps"] == "see description"
assert len(draft_rules("x" * 100)["title"]) == 60

# Triage: priority levels, and the first matching rule wins.
assert triage_rules("the app crashes")[0].startswith("HIGH")
assert triage_rules("checkout is slow")[0].startswith("MEDIUM")
assert triage_rules("button colour is off")[0].startswith("LOW")
assert triage_rules("slow, then it crashed")[0].startswith("HIGH")
# Whole-word starts only: "download" isn't "down", "almost" isn't "lost".
assert triage_rules("the download page has a typo, almost fine")[0].startswith("LOW")

# Triage reads JSON and plain text the same way — same answer either way.
for report in ["the app crashes when I upload big files",
               "Checkout is slow in Chrome. Steps: 1. add item 2. click pay",
               "Upload of a 5 MB file fails on Android"]:
    draft = draft_rules(report)
    assert triage_rules(json.dumps(draft, indent=2)) == triage_rules(to_text(draft)), report
assert triage_rules(to_text(d))[1] == ["steps to reproduce", "device / browser", "file size tested"]
assert "file size tested" not in triage_rules(to_text(draft_rules("Upload of a 5 MB file fails")))[1]

# JSON handoff check: accepts a full form (even wrapped in ```json), rejects the rest.
good = json.dumps(d)
assert check_json(good) == (d, None)
assert check_json(f"```json\n{good}\n```") == (d, None)
assert check_json("Sure! Here is the report: {")[1] == "Draft wasn't valid JSON"
assert check_json("[1, 2]")[1] == "Draft was JSON, but not a report form"
assert "missing field(s): steps" in check_json(json.dumps({k: "x" for k in FIELDS if k != "steps"}))[1]

print("All checks passed.")
