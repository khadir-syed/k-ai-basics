"""PII Redaction Demo — black out personal data (SSNs, card numbers, emails)
in a document before an AI ever sees it, then check what slipped through.
"""
import argparse
import glob
import json
import os
import re
from collections import Counter

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")

# The patterns: one short, simple regex per kind of personal data.
# Intentionally NOT complete — the [MISSED] lines show what they can't catch.
PATTERNS = {
    "CARD": r"\b(?:\d{4}[ -]?){3}\d{4}\b",     # 16 digits, maybe in groups of 4
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",           # 123-45-6789, dashes only
    "EMAIL": r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+",  # name@example.com
}

WHY_MISSED = {
    "NAME": "a regex can't tell a name from any other word",
    "SSN": "written in a format the pattern doesn't expect",
    "CARD": "written in a format the pattern doesn't expect",
    "EMAIL": "written in a format the pattern doesn't expect",
}


def load_docs(docs_dir=DOCS_DIR):
    """Return [(filename, text)] for every .txt file, whitespace collapsed."""
    docs = []
    for path in sorted(glob.glob(os.path.join(docs_dir, "*.txt"))):
        with open(path, encoding="utf-8") as fh:
            docs.append((os.path.basename(path), " ".join(fh.read().split())))
    return docs


def load_answer_key(docs_dir=DOCS_DIR):
    with open(os.path.join(docs_dir, "answer_key.json"), encoding="utf-8") as fh:
        return {k: v for k, v in json.load(fh).items() if not k.startswith("_")}


def redact(text):
    """Replace every pattern match with a [REDACTED-KIND] label.
    Returns (redacted_text, Counter of matches per kind)."""
    counts = Counter()
    for kind, pattern in PATTERNS.items():
        text, n = re.subn(pattern, f"[REDACTED-{kind}]", text)
        counts[kind] += n
    return text, counts


def missed(redacted_text, answers):
    """Every answer-key item still visible in the redacted text."""
    return [(kind, value) for kind, value in answers if value in redacted_text]


def run():
    answer_key = load_answer_key()
    total_caught, total_missed, total_items = Counter(), [], 0

    for name, text in load_docs():
        answers = answer_key.get(name, [])
        total_items += len(answers)
        print(f"── {name} " + "─" * (60 - len(name)))
        print(f'{"[UNREDACTED]":<13}"{text}"')
        redacted, counts = redact(text)
        found = ", ".join(f"{k} ({n})" for k, n in counts.items() if n) or "none"
        print(f"{'[SCANNING]':<13}Regex patterns matched: {found}")
        print(f'{"[REDACTED]":<13}"{redacted}"')
        doc_missed = missed(redacted, answers)
        for kind, value in doc_missed:
            print(f'{"[MISSED]":<13}{kind} "{value}" — {WHY_MISSED[kind]}.')
        total_caught += counts
        total_missed += doc_missed
        print()

    caught = total_items - len(total_missed)
    kinds = ", ".join(f"{k} {n}" for k, n in total_caught.items())
    print("── SUMMARY " + "─" * 53)
    print(f"[CAUGHT]     {caught} of {total_items} pieces of personal data. Pattern matches: {kinds}.")
    missed_kinds = ", ".join(f"{k} {n}" for k, n in Counter(k for k, _ in total_missed).items())
    print(f"[MISSED]     {len(total_missed)} ({missed_kinds}).")
    print("[LESSON]     Simple patterns catch the tidy cases. Names and oddly written")
    print("             data slip through — redaction isn't solved by one regex pass.")


if __name__ == "__main__":
    argparse.ArgumentParser(
        description="PII Redaction Demo — fully offline, no --key mode on purpose.").parse_args()
    run()
