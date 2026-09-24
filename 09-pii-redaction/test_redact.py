"""Self-check for the redaction patterns and the answer-key comparison.
Runs instantly, no network. Run with: python test_redact.py
"""
from redact import load_answer_key, load_docs, missed, redact

docs = dict(load_docs())
key = load_answer_key()

# The answer key covers exactly the sample docs, and every item really is in them
# (catches a typo in answer_key.json that would make a miss look like a catch).
assert set(docs) == set(key), (set(docs), set(key))
for name, answers in key.items():
    for kind, value in answers:
        assert value in docs[name], (name, value)

# Tidy formats are caught and replaced with a label.
text, counts = redact("SSN 000-12-3456, card 4111 1111 1111 1111, mail a.b@example.com")
assert text == "SSN [REDACTED-SSN], card [REDACTED-CARD], mail [REDACTED-EMAIL]", text
assert counts == {"CARD": 1, "SSN": 1, "EMAIL": 1}, counts
assert redact("5555-5555-5555-4444")[0] == "[REDACTED-CARD]"

# Odd formats and names get through (that's the lesson).
for leak in ["000 45 6789", "sam dot taylor at example dot com", "Jane Doe"]:
    assert redact(leak)[0] == leak, leak

# Ordinary numbers are left alone.
assert redact("Order 12345 arrived on 2026-09-24 at 10:30.")[1] == {"CARD": 0, "SSN": 0, "EMAIL": 0}

# missed() reports only what is still visible after redaction.
answers = [["NAME", "John Smith"], ["SSN", "000-12-3456"]]
assert missed(redact("John Smith, 000-12-3456")[0], answers) == [("NAME", "John Smith")]

# Across all sample docs: 5 of 11 caught, and every miss is a name or an odd format.
all_missed = [m for name, text in docs.items() for m in missed(redact(text)[0], key[name])]
assert sum(len(v) for v in key.values()) == 11 and len(all_missed) == 6, all_missed
assert [k for k, _ in all_missed].count("NAME") == 4

print("All checks passed.")
