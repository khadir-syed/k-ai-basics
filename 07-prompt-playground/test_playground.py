"""Self-check for the checklist, the pairs and the trimming. Runs instantly, no
network. Run with: python test_playground.py
"""
from playground import CHECKS, PAIRS, check_prompt, score, trim


def passed(prompt):
    return {name for name, _, ok in check_prompt(prompt) if ok}


# Each pair's "what changed" notes must match exactly what the checklist sees
# the improved prompt gain — so the demo never contradicts itself.
for pair in PAIRS:
    gained = passed(pair["improved"]) - passed(pair["vague"])
    assert {name for name, _ in pair["changes"]} == gained, (pair["name"], gained)
    assert score(pair["improved"]) > score(pair["vague"]), pair["name"]

assert score("Write about dogs") == 0
assert passed("You are a friendly vet") == {"Role"}
assert passed("Keep it under 50 words") == {"Limit"}
assert passed("in 4 short sentences") == {"Limit"}
assert passed("Summarise this article in under 50 words for busy managers") == {
    "Specific", "Format", "Limit", "Audience"}
assert passed("Give me 3 tips for new runners") == {"Limit", "Audience"}
assert "Audience" not in passed("asking for a day off")  # "for a" alone isn't an audience
assert len(CHECKS) == 5

# The checklist spots ingredients, not quality: this nonsense still scores 4/5.
assert score("You are a list of 5 words for kids") == 4

# Trimming: short text untouched, long text cut to 12 lines with a note.
assert trim("one\ntwo") == "one\ntwo"
long = trim("\n".join(f"line {i}" for i in range(20)))
assert long.splitlines()[:12] == [f"line {i}" for i in range(12)]
assert long.splitlines()[-1] == "(… trimmed for space: 8 more lines)"
assert len(trim("word " * 200).splitlines()) == 13  # one long line gets wrapped, then cut
assert trim("\n".join("x" * 13)).endswith("(… trimmed for space: 1 more line)")

print("All checks passed.")
