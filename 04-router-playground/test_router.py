"""Self-check for router.py. Run: python test_router.py"""

from router import route, score_skill, SKILLS

bug_fixer = next(s for s in SKILLS if s["name"] == "bug-fixer")
writer = next(s for s in SKILLS if s["name"] == "writer")

# Scoring is matched-keywords / total-keywords-for-that-skill.
score, matched = score_skill("fix the bug where login fails silently", bug_fixer)
assert matched == ["bug", "fails", "fix"], matched
assert abs(score - 3 / 7) < 1e-9, score

# A request with no keyword overlap at all scores 0.
score, matched = score_skill("what's the weather today", bug_fixer)
assert score == 0.0 and matched == []

# Routes to the clearly best-matching skill.
best, _ = route("fix the bug where login fails silently")
assert best["name"] == "bug-fixer", best

best, _ = route("write a blog post about our new feature")
assert best["name"] == "writer", best

# Below-threshold requests return no match instead of forcing a guess.
best, _ = route("what's the weather today")
assert best is None, best

print("All router.py checks passed.")
