"""Context Window Explorer — watch an AI "forget" the oldest messages once a
conversation grows past its token budget.
"""
import argparse
import os
import sys

DEFAULT_BUDGET = 30


def load_tokenizer():
    """Downloads GPT-2's tokenizer (a few MB) on first run, then caches it.

    Only the tokenizer is needed to count tokens — not the full GPT-2 model.
    """
    # Hide "PyTorch was not found" — this demo never needs PyTorch.
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    try:
        from huggingface_hub.utils import logging as hf_logging
        from transformers import GPT2Tokenizer

        hf_logging.set_verbosity_error()
    except ImportError:
        sys.exit("Missing packages. Run: pip install -r requirements.txt")

    try:
        return GPT2Tokenizer.from_pretrained("gpt2")
    except Exception as exc:
        sys.exit(
            "Could not download the GPT-2 tokenizer. This demo needs an internet "
            "connection the first time you run it (it's cached locally after "
            f"that).\n\nDetails: {exc}"
        )


def add_message(window, text, tokens, budget):
    """Append (text, tokens) to window, dropping the oldest messages until the
    total fits the budget. Changes window in place.

    Returns the list of dropped (text, tokens), or None if this one message is
    bigger than the whole budget (it is not added at all).
    """
    if tokens > budget:
        return None
    window.append((text, tokens))
    dropped = []
    while sum(t for _, t in window) > budget:
        dropped.append(window.pop(0))
    return dropped


def fill_bar(used, budget, width=20):
    filled = round(used / budget * width)
    return "[" + "#" * filled + "." * (width - filled) + "]"


def short(text, limit=50):
    return text if len(text) <= limit else text[: limit - 3] + "..."


def explore(budget):
    tokenizer = load_tokenizer()
    window, sent, forgotten = [], 0, 0

    print(f'\n[BUDGET]   {budget} tokens — the AI can only "see" this many tokens at once.')
    if budget == DEFAULT_BUDGET:
        print("           (That's the default. Want a bigger notepad? Restart with: "
              "python explore.py --budget 100)")
    print("Type a message and press Enter. Type 'quit' when you're done.\n")

    while True:
        try:
            line = input("you> ")
        except EOFError:
            break
        if not sys.stdin.isatty():
            print(line)  # echo piped input so the transcript reads naturally
        line = line.strip()
        if line.lower() == "quit":
            break
        if not line:
            continue

        tokens = len(tokenizer.encode(line))
        print(f'[ADD]      "{short(line)}" (+{tokens} tokens)')
        dropped = add_message(window, line, tokens, budget)
        if dropped is None:
            print(f"[TOO BIG]  This one message is {tokens} tokens — bigger than the "
                  f"whole {budget}-token budget, so it can't fit at all. Skipped.")
            print(f"           Your earlier messages are still safe. To fit messages this "
                  f"long, restart with: python explore.py --budget {tokens * 2}\n")
            continue

        sent += 1
        if dropped:
            print("[OVER BUDGET] Dropping the oldest message to make room:")
            for text, t in dropped:
                print(f'   ✗ REMOVED: "{short(text)}" ({t} tokens)')
            forgotten += len(dropped)

        used = sum(t for _, t in window)
        print(f"[CURRENT]  {used}/{budget} tokens {fill_bar(used, budget)} "
              f"— {len(window)} message(s) remembered\n")

    print(f"\n[SUMMARY]  You sent {sent} message(s). The AI forgot {forgotten} of them "
          "(always the oldest ones first).")
    if window:
        print("[STILL REMEMBERS]")
        for i, (text, t) in enumerate(window, 1):
            print(f'   {i}. "{short(text)}" ({t} tokens)')
    if forgotten:
        print("[TAKEAWAY] This is why long chats can lose track of something you said early on.")
    else:
        print("[TAKEAWAY] Nothing was forgotten yet — send more messages, or try a "
              "smaller --budget, and watch the oldest ones disappear.")


def main():
    parser = argparse.ArgumentParser(description="Context Window Explorer")
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET,
                        help=f"how many tokens the AI can see at once (default {DEFAULT_BUDGET})")
    args = parser.parse_args()
    if args.budget < 1:
        parser.error("--budget must be at least 1")
    explore(args.budget)


if __name__ == "__main__":
    main()
