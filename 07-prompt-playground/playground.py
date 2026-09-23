"""Prompt Engineering Playground — see how small wording changes to a prompt
change the answer, and check your own prompt against a simple checklist.
"""
import argparse
import datetime
import json
import os
import re
import sys
import textwrap
import urllib.error

import llm

SAVED_FILE = os.path.join(os.path.dirname(__file__), "saved_answers.json")
SHOW_LINES = 12  # long answers are trimmed to this many lines on screen
MAX_TOKENS = 1500  # room for "thinking" models plus a full answer

PAIRS = [
    {
        "name": "Too vague",
        "vague": "Write about dogs",
        "improved": "Write a 3-sentence, upbeat product description for a dog leash, "
                    "aimed at first-time dog owners.",
        "changes": [
            ("Specific", 'a dog leash, not "dogs" in general'),
            ("Format", "a product description"),
            ("Limit", "3 sentences, so it can't ramble"),
            ("Audience", "first-time dog owners, so it picks the right words"),
        ],
    },
    {
        "name": "No format",
        "vague": "Tell me about exercise",
        "improved": "Give me 3 bullet points, one line each, on easy ways a busy "
                    "office worker can exercise at home.",
        "changes": [
            ("Format", "bullet points"),
            ("Limit", "3 points, one line each"),
            ("Specific", "easy exercise at home, not all of exercise"),
            ("Audience", "a busy office worker"),
        ],
    },
    {
        "name": "No limits",
        "vague": "Write an email asking for a day off",
        "improved": "Write a polite email to my manager asking for a day off on "
                    "Friday 3 October. Keep it under 80 words.",
        "changes": [
            ("Limit", "under 80 words"),
            ("Specific", "which day, and a polite tone"),
            ("Audience", "my manager"),
        ],
    },
    {
        "name": "No role or audience",
        "vague": "Explain taxes",
        "improved": "You are a friendly teacher. Explain what taxes are to a "
                    "10-year-old in 4 short sentences, using a lemonade stand as "
                    "the example.",
        "changes": [
            ("Role", "a friendly teacher"),
            ("Audience", "a 10-year-old"),
            ("Limit", "4 short sentences"),
            ("Specific", "a lemonade stand example"),
        ],
    },
]

# ---- The checklist -------------------------------------------------------
# Simple word-spotting rules. They check whether a prompt *mentions* each
# ingredient — not whether the prompt is actually good.

_NUM_UNIT = r"\b\d+[\s-]+(\w+\s+)?(words?|sentences?|lines?|points?|bullets?|paragraphs?|characters?|items?|steps?|tips?|ideas?|examples?|reasons?|ways|questions?)\b"

CHECKS = [
    ("Specific", "say exactly what you want, with details (10+ words)",
     lambda p: len(p.split()) >= 10),
    ("Role", 'say who should answer, e.g. "You are a friendly vet..."',
     lambda p: re.search(r"\b(you are|you're|act as|pretend to be|imagine you are)\b", p)),
    ("Format", 'say the shape, e.g. "3 bullet points" or "a short email"',
     lambda p: re.search(r"\b(bullets?|list|table|steps?|json|points|numbered|"
                         r"headlines?|poem|email|letter|description|summary|summari[sz]e|essay|"
                         r"story|outline)\b", p)),
    ("Limit", 'say how long, e.g. "under 50 words" or "in 3 sentences"',
     lambda p: re.search(_NUM_UNIT, p) or re.search(
         r"\b(under|at most|no more than|maximum|up to|fewer than|less than|"
         r"keep it (short|brief))\b", p)),
    ("Audience", 'say who it is for, e.g. "for a 10-year-old" or "for my manager"',
     lambda p: re.search(r"\b(aimed at|audience|readers?|\d+-year-old|beginners?|"
                         r"owners?|workers?|students?|kids|children|customers?|"
                         r"managers?|boss|team|for (new|first-time|busy|young|older|"
                         r"beginner) \w+)\b", p)),
]


def check_prompt(prompt):
    """Return a list of (name, tip, passed) for every checklist item."""
    lowered = prompt.lower()
    return [(name, tip, bool(rule(lowered))) for name, tip, rule in CHECKS]


def score(prompt):
    return sum(passed for _, _, passed in check_prompt(prompt))


def show_checklist(prompt):
    results = check_prompt(prompt)
    total = sum(passed for _, _, passed in results)
    missing = [name.lower() for name, _, passed in results if not passed]
    bar = "#" * (total * 2) + "." * ((len(CHECKS) - total) * 2)

    print(f'\n[YOUR PROMPT] "{prompt}"\n')
    print(f"Checklist score: {total}/{len(CHECKS)}  [{bar}]")
    for name, tip, passed in results:
        if passed:
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name:<9} tip: {tip}")
    summary = "missing: " + ", ".join(missing) if missing else "nothing missing"
    print(f"\nScore {total}/{len(CHECKS)} — {summary}")
    print("(A checklist score, not a quality grade: it only spots the ingredients.)\n")


# ---- Showing answers -----------------------------------------------------

def trim(text, max_lines=SHOW_LINES, width=76):
    """Wrap text to the terminal width and keep only the first max_lines lines."""
    lines = []
    for line in text.splitlines() or [""]:
        lines.extend(textwrap.wrap(line, width) or [""])
    if len(lines) <= max_lines:
        return "\n".join(lines)
    hidden = len(lines) - max_lines
    more = "1 more line" if hidden == 1 else f"{hidden} more lines"
    return "\n".join(lines[:max_lines]) + f"\n(… trimmed for space: {more})"


def load_saved():
    try:
        with open(SAVED_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None


def live_answer(prompt):
    try:
        answer = llm.ask(prompt, max_tokens=MAX_TOKENS)
    except urllib.error.URLError as exc:
        sys.exit(f"The live API call failed (check your key and internet): {exc}")
    return answer or ("(The model sent back no words — it may have used all its room "
                      "thinking. Try again or try a different model.)")


def show_pair(number, use_key=False):
    pair = PAIRS[number - 1]
    print(f"\n══ Pair {number}: {pair['name']} ══\n")
    print(f'VAGUE PROMPT:    "{pair["vague"]}"')
    print(f'IMPROVED PROMPT: "{pair["improved"]}"\n')
    print("What changed, and why it helps:")
    for name, why in pair["changes"]:
        print(f"  + {name}: {why}")
    print(f"\nChecklist score: vague {score(pair['vague'])}/{len(CHECKS)} → "
          f"improved {score(pair['improved'])}/{len(CHECKS)}")

    if use_key:
        label = f"🔑 Live answer from {llm.current_model()}"
        answers = {side: live_answer(pair[side]) for side in ("vague", "improved")}
    else:
        saved = load_saved()
        if saved is None:
            print("\n(No saved example answers yet. Add --key to ask a real model.)\n")
            return
        label = f"📄 Saved real answer from {saved['model']}, {saved['date']}"
        answers = saved["pairs"][number - 1]

    for side in ("vague", "improved"):
        print(f"\n── Answer to the {side.upper()} prompt ── {label}\n")
        print(trim(answers[side]))
    print()


def save_examples():
    """Maintainer tool: ask the live model every pair and save the answers."""
    pairs = []
    for number, pair in enumerate(PAIRS, 1):
        print(f"Asking pair {number}/{len(PAIRS)}...")
        pairs.append({side: live_answer(pair[side]) for side in ("vague", "improved")})
    data = {"model": llm.current_model(),
            "date": datetime.date.today().strftime("%d %B %Y").lstrip("0"),
            "pairs": pairs}
    with open(SAVED_FILE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"Saved {len(pairs)} pairs of answers from {data['model']} to saved_answers.json")


# ---- Menu ----------------------------------------------------------------

def menu(use_key=False):
    while True:
        print("\nPick a pair to compare, or check your own prompt:\n")
        for number, pair in enumerate(PAIRS, 1):
            print(f"  {number}. {pair['name']:<20} \"{pair['vague']}\"")
        print(f"  {len(PAIRS) + 1}. Check my own prompt")
        print("  q. Quit\n")
        try:
            choice = input("Your choice: ").strip().lower()
        except EOFError:
            return
        if not sys.stdin.isatty():
            print(choice)  # echo piped input so the transcript reads naturally
        if choice == "q":
            return
        if choice.isdigit() and 1 <= int(choice) <= len(PAIRS):
            show_pair(int(choice), use_key)
        elif choice == str(len(PAIRS) + 1):
            try:
                prompt = input("Type your prompt: ").strip()
            except EOFError:
                return
            if not sys.stdin.isatty():
                print(prompt)
            if prompt:
                show_checklist(prompt)
        else:
            print(f"Please type a number from 1 to {len(PAIRS) + 1}, or q.")


def main():
    parser = argparse.ArgumentParser(description="Prompt Engineering Playground")
    parser.add_argument("--pair", type=int, choices=range(1, len(PAIRS) + 1),
                        help="show one pair and exit")
    parser.add_argument("--check", metavar="PROMPT", help="check one prompt and exit")
    parser.add_argument("--key", action="store_true",
                        help="ask a real AI model for both answers (needs an API key)")
    parser.add_argument("--save-examples", action="store_true",
                        help="maintainers: save live answers to saved_answers.json")
    args = parser.parse_args()

    if (args.key or args.save_examples) and not llm.has_key():
        sys.exit("No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
                 "or run without --key.")
    if args.save_examples:
        save_examples()
    elif args.check is not None:
        show_checklist(args.check)
    elif args.pair:
        show_pair(args.pair, args.key)
    else:
        menu(args.key)


if __name__ == "__main__":
    main()
