"""Tiny helper for --key mode: send one prompt to a live AI model, get text back.

This exact file is copied into every demo folder that has a simple --key mode,
so each folder still works on its own. Run `python check_llm_copies.py` from
the repo root to make sure the copies are still identical.
"""
import json
import os
import urllib.request

# Models used by --key mode. Swap in a newer model name here if you like.
ANTHROPIC_MODEL = "claude-haiku-4-5"
OPENAI_MODEL = "gpt-4o-mini"

# Optional environment variables, all off by default:
#   LLM_MODEL           use this model name instead of the two above
#   ANTHROPIC_BASE_URL  send Anthropic-style calls here (default https://api.anthropic.com)
#   OPENAI_BASE_URL     send OpenAI-style calls here, e.g. a local AI gateway
#                       (default https://api.openai.com/v1)


def has_key():
    """True if ANTHROPIC_API_KEY or OPENAI_API_KEY is set."""
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def current_model():
    """The model name ask() will use right now."""
    if os.environ.get("LLM_MODEL"):
        return os.environ["LLM_MODEL"]
    return ANTHROPIC_MODEL if os.environ.get("ANTHROPIC_API_KEY") else OPENAI_MODEL


def _post_json(url, headers, payload):
    # Name ourselves: some services behind Cloudflare (e.g. Groq) block
    # Python's default "Python-urllib" User-Agent with a 403.
    headers = {**headers, "User-Agent": "k_ai-basics-demo"}
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ask(prompt, max_tokens=300):
    """Send one prompt and return the reply text. Uses Anthropic if its key is
    set, otherwise OpenAI. Call has_key() first.

    Raises urllib.error.URLError if the call fails (no internet, bad key, ...).
    """
    messages = [{"role": "user", "content": prompt}]
    model = current_model()

    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        base = os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com"
        data = _post_json(
            base.rstrip("/") + "/v1/messages",
            {"x-api-key": key, "anthropic-version": "2023-06-01",
             "content-type": "application/json"},
            {"model": model, "max_tokens": max_tokens, "messages": messages},
        )
        return " ".join(b["text"] for b in data["content"] if b["type"] == "text").strip()

    base = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    data = _post_json(
        base.rstrip("/") + "/chat/completions",
        {"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
         "content-type": "application/json"},
        {"model": model, "max_tokens": max_tokens, "messages": messages},
    )
    # "or ''": some thinking models return no text if they run out of room.
    return (data["choices"][0]["message"]["content"] or "").strip()
