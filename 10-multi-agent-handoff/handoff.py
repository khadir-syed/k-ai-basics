"""Multi-Agent Handoff — watch two agents work as a team: a Drafter turns a
messy bug description into a report, then hands it to a Triage agent that
decides how urgent it is and what's missing.
"""
import argparse
import json
import re
import sys
import urllib.error

import llm

FIELDS = ["title", "description", "severity", "steps", "environment"]
NOT_PROVIDED = "not provided"

# ---- Rule-based agents (default mode) --------------------------------

ENVIRONMENT_WORDS = ["iphone", "android", "ipad", "windows", "mac", "linux",
                     "chrome", "safari", "firefox", "edge"]

# Triage rules, checked top to bottom: the first match sets the priority.
PRIORITY_RULES = [
    ("HIGH", ["crash", "data loss", "lost", "security", "can't log in",
              "cannot log in", "outage", "payment", "charged"]),
    ("MEDIUM", ["slow", "error", "fails", "broken", "doesn't work", "timeout",
                "times out", "freeze"]),
]


def draft_rules(report):
    """Drafter: fill in the bug-report form from the user's own words."""
    text = " ".join(report.split())
    first = re.split(r"(?<=[.!?])\s+", text)[0]
    title = first[0].upper() + first[1:] if first else ""
    if len(title) > 60:
        title = title[:57].rstrip() + "..."
    env = [w for w in ENVIRONMENT_WORDS if re.search(rf"\b{w}\b", text, re.IGNORECASE)]
    has_steps = re.search(r"\bsteps?\b|\b1[.)]\s", text, re.IGNORECASE)
    return {
        "title": title,
        "description": text,
        "severity": "unknown",  # the Drafter writes; deciding urgency is Triage's job
        "steps": "see description" if has_steps else NOT_PROVIDED,
        "environment": ", ".join(env) if env else NOT_PROVIDED,
    }


def triage_rules(draft_text):
    """Triage: read the draft (JSON or plain text — it just reads the words),
    return (priority line, list of missing info)."""
    low = draft_text.lower()
    priority = "LOW (no crash, error or slowness mentioned)"
    for level, words in PRIORITY_RULES:
        # \b = match at the start of a word, so "crash" finds "crashes"
        # but "lost" doesn't fire in the middle of "almost".
        hit = next((w for w in words if re.search(rf"\b{re.escape(w)}", low)), None)
        if hit:
            priority = f'{level} ("{hit}" reported)'
            break
    missing = []
    if re.search(rf'"?steps"?\s*:\s*"?{NOT_PROVIDED}', low):
        missing.append("steps to reproduce")
    if re.search(rf'"?environment"?\s*:\s*"?{NOT_PROVIDED}', low):
        missing.append("device / browser")
    if re.search(r"\b(upload|file)", low) and not re.search(r"\d+\s?(kb|mb|gb)\b", low):
        missing.append("file size tested")
    return priority, missing


# ---- The handoff: how the draft travels between agents ----------------

def to_text(draft):
    return "\n".join(f"{k.capitalize()}: {draft[k]}" for k in FIELDS)


def check_json(raw):
    """JSON handoff: the draft must be a JSON object with every field.
    Returns (draft dict, None) or (None, reason it failed)."""
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip())  # forgive ```json wrappers
    try:
        draft = json.loads(raw)
    except json.JSONDecodeError:
        return None, "Draft wasn't valid JSON"
    if not isinstance(draft, dict):
        return None, "Draft was JSON, but not a report form"
    missing = [f for f in FIELDS if f not in draft]
    if missing:
        return None, f"Draft is missing field(s): {', '.join(missing)}"
    return draft, None


# ---- Live agents (--key mode) -----------------------------------------

def drafter_prompt(report, handoff):
    fmt = ("Reply with ONLY a JSON object with exactly these keys: "
           + ", ".join(FIELDS) + "." if handoff == "json" else
           "Reply as plain text, one line per field: "
           + ", ".join(f"{f.capitalize()}:" for f in FIELDS))
    return ("You are the Drafting Agent on a support team. Turn the user's bug "
            "description into a bug report. Keep severity as \"unknown\" — "
            f"another agent decides that. Use \"{NOT_PROVIDED}\" for anything "
            f"the user didn't say. {fmt}\n\nBug description:\n<<<\n{report}\n>>>")


def triage_prompt(draft_text):
    return ("You are the Triage Agent on a support team. Another agent drafted "
            "this bug report. Decide its priority and what information is "
            "missing. Severity is left as \"unknown\" on purpose — your "
            "priority decides it, so don't list it as missing. "
            "Reply in exactly two lines:\n"
            "Priority: HIGH, MEDIUM or LOW (short reason)\n"
            "Missing: comma-separated list, or none\n\n"
            f"Draft:\n<<<\n{draft_text}\n>>>")


def live(prompt):
    try:
        reply = llm.ask(prompt, max_tokens=1000)  # room for "thinking" models
    except urllib.error.URLError as exc:
        sys.exit(f"The live API call failed (check your key and internet): {exc}")
    return reply or "(The model sent back no words — try again or another model.)"


# ---- The run ------------------------------------------------------------

def say(agent, text):
    lines = str(text).splitlines() or [""]
    print(f"{agent:<20}{lines[0]}")
    for line in lines[1:]:
        print(" " * 20 + line)


def run(report, handoff="json", use_key=False):
    d, t = "[AGENT 1: Drafter]", "[AGENT 2: Triage]"
    if use_key:
        print(f"🔑 Live API — two real model calls ({llm.current_model()}), one per agent.")
    else:
        print("📋 Rule-based — both agents follow simple, visible rules.")
    print(f"Handoff format: {handoff}\n")

    say(d, f'Received: "{report}"')
    if use_key:
        output = live(drafter_prompt(report, handoff))
    else:
        draft = draft_rules(report)
        output = json.dumps(draft, indent=2) if handoff == "json" else to_text(draft)
    say(d, "Output →")
    say("", output)

    if handoff == "json":
        print("[HANDOFF] Passing draft to Triage Agent as JSON...")
        draft, problem = check_json(output)
        if problem:
            print(f"[HANDOFF FAILED] {problem}. The Triage Agent never got it.")
            print("[LESSON] A strict format catches a broken handoff early. "
                  "Try --handoff text to see the forgiving way.")
            return
        print(f"[HANDOFF] Checked: valid JSON with all {len(FIELDS)} fields ✓")
        handed_over = json.dumps(draft, indent=2)
    else:
        print("[HANDOFF] Passing draft to Triage Agent as plain text...")
        print("[HANDOFF] Nothing checks its shape — the Triage Agent reads it as-is.")
        handed_over = output

    say(t, "Reviewing draft...")
    if use_key:
        say(t, live(triage_prompt(handed_over)))
    else:
        priority, missing = triage_rules(handed_over)
        say(t, f"Priority: {priority}")
        flagged = ", ".join(f'"{m}"' for m in missing) or "none"
        say(t, f"Missing info flagged: {flagged}")
    print("[FINAL OUTPUT] Structured, triaged bug report ready for a human.")


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent Handoff")
    parser.add_argument("report", help="describe a bug or issue, in quotes")
    parser.add_argument("--handoff", choices=["json", "text"], default="json",
                        help="how the Drafter passes its report to Triage (default: json)")
    parser.add_argument("--key", action="store_true",
                        help="make both agents real AI model calls (needs an API key)")
    args = parser.parse_args()

    if args.key and not llm.has_key():
        sys.exit("No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
                 "or run without --key.")
    if not args.report.strip():
        sys.exit("Please describe a bug, e.g. python handoff.py \"the app crashes\"")
    run(args.report, handoff=args.handoff, use_key=args.key)


if __name__ == "__main__":
    main()
