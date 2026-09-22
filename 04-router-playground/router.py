"""Router Playground — shows how a system decides which "skill" fits a request.

Default mode: rule-based keyword-overlap scoring, fully offline, deterministic.
Optional --key mode: asks a real LLM to make the same routing decision, so you
can compare rule-based vs LLM-based routing on the same input.
"""

import argparse
import json
import os
import re
import urllib.request

# Each skill is trigger keywords + a one-line description. Score for a given
# request = (keywords found in the request) / (total keywords for that skill).
SKILLS = [
    {
        "name": "bug-fixer",
        "description": "Diagnoses and fixes broken or crashing code.",
        "keywords": ["bug", "error", "crash", "broken", "fails", "exception", "fix"],
    },
    {
        "name": "writer",
        "description": "Drafts blog posts, articles, and other written content.",
        "keywords": ["draft", "write", "blog", "article", "post", "copy", "essay", "content"],
    },
    {
        "name": "release-notes-helper",
        "description": "Writes changelog entries for a new release.",
        "keywords": ["changelog", "release", "version", "notes", "ship", "deploy", "update"],
    },
]

THRESHOLD = 0.2

_WORD_RE = re.compile(r"[a-z0-9']+")


def _tokenize(text):
    return set(_WORD_RE.findall(text.lower()))


def score_skill(request, skill):
    """Return (score, matched_keywords) for one skill against one request."""
    tokens = _tokenize(request)
    matched = sorted(k for k in skill["keywords"] if k in tokens)
    score = len(matched) / len(skill["keywords"])
    return score, matched


def route(request):
    """Score every skill and return (best_skill_or_None, all_results).

    all_results is a list of (skill, score, matched) in SKILLS order, so the
    caller can print every skill's score before announcing the winner.
    """
    results = [(skill, *score_skill(request, skill)) for skill in SKILLS]
    best_skill, best_score, _ = max(results, key=lambda r: r[1])
    if best_score < THRESHOLD:
        return None, results
    return best_skill, results


def run_rule_based(request):
    print(f'[REQUEST]  "{request}"')
    best_skill, results = route(request)
    for skill, score, matched in results:
        matched_str = f"  (matched: {', '.join(matched)})" if matched else ""
        print(f"[CHECKING] {skill['name']:<21} -> score: {score:.2f}{matched_str}")
    if best_skill is None:
        print("[NO CONFIDENT MATCH] No skill scored above the threshold "
              f"({THRESHOLD}) — a real router would ask a human instead of guessing.")
        return
    print(f"[ROUTED TO] {best_skill['name']}")
    print("[WHY] Highest keyword overlap with this skill's trigger terms.")
    print("📋 Rule-based")


def _post_json(url, headers, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _skills_prompt(request):
    skill_lines = "\n".join(f"- {s['name']}: {s['description']}" for s in SKILLS)
    return (
        f"Here are the available skills:\n{skill_lines}\n\n"
        f'Request: "{request}"\n\n'
        "Which single skill best fits this request? If none fit well, say so. "
        'Reply with exactly two lines:\nROUTED TO: <skill-name or "none">\n'
        "WHY: <one sentence>"
    )


def _call_anthropic(request):
    key = os.environ["ANTHROPIC_API_KEY"]
    payload = {
        "model": "claude-3-5-haiku-latest",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": _skills_prompt(request)}],
    }
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    result = _post_json("https://api.anthropic.com/v1/messages", headers, payload)
    return result["content"][0]["text"]


def _call_openai(request):
    key = os.environ["OPENAI_API_KEY"]
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": _skills_prompt(request)}],
    }
    headers = {"Authorization": f"Bearer {key}", "content-type": "application/json"}
    result = _post_json("https://api.openai.com/v1/chat/completions", headers, payload)
    return result["choices"][0]["message"]["content"]


def run_with_llm(request):
    print(f'[REQUEST]  "{request}"')
    if os.environ.get("ANTHROPIC_API_KEY"):
        reply = _call_anthropic(request)
    elif os.environ.get("OPENAI_API_KEY"):
        reply = _call_openai(request)
    else:
        print("[ERROR] --key was passed but no ANTHROPIC_API_KEY or "
              "OPENAI_API_KEY is set in the environment.")
        return
    for line in reply.strip().splitlines():
        if line.startswith("ROUTED TO:"):
            print(f"[ROUTED TO] {line.split(':', 1)[1].strip()}")
        elif line.startswith("WHY:"):
            print(f"[WHY] {line.split(':', 1)[1].strip()}")
        else:
            print(line)
    print("🔑 LLM-routed")


def main():
    parser = argparse.ArgumentParser(description="Router Playground")
    parser.add_argument("request", help="the request to route, in quotes")
    parser.add_argument("--key", action="store_true",
                         help="use a real LLM to route instead of keyword scoring")
    args = parser.parse_args()

    if args.key:
        run_with_llm(args.request)
    else:
        run_rule_based(args.request)


if __name__ == "__main__":
    main()
