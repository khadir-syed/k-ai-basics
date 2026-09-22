"""Agent Trace CLI — watch an "agent" decide whether to use a tool, use it,
and answer, one step at a time.
"""
import ast
import json
import operator
import os
import re
import sys
import urllib.error
import urllib.request

TRIVIA = {
    "how many moons does jupiter have": (
        "Jupiter has 95 confirmed moons — the most of any planet in our solar system."
    ),
    "who invented the light bulb": (
        "Thomas Edison is often credited with inventing the practical light bulb "
        "in 1879, building on earlier work by inventors like Humphry Davy and Joseph Swan."
    ),
    "what is the tallest mountain in the world": (
        "Mount Everest, standing about 8,849 meters (29,032 feet) tall, on the "
        "border of Nepal and Tibet."
    ),
    "how long do octopuses live": (
        "Most octopus species live only 1 to 2 years — surprisingly short for "
        "such an intelligent animal."
    ),
    "what is the fastest land animal": (
        "The cheetah, which can sprint up to about 100-120 km/h (60-75 mph) in "
        "short bursts."
    ),
    "how many bones does a human body have": (
        "An adult human body has 206 bones, though babies are born with about "
        "270 that fuse together over time."
    ),
}

STOPWORDS = {"a", "an", "the", "is", "are", "do", "does", "in", "of", "what", "how", "who"}


# ---- Tool 1: calculator -----------------------------------------------

_MATH_WORDS = [
    ("divided by", "/"),
    ("multiplied by", "*"),
    ("times", "*"),
    ("plus", "+"),
    ("minus", "-"),
]
_EXPR_RE = re.compile(r"[-+]?\d+(\.\d+)?(\s*[-+*/]\s*[-+]?\d+(\.\d+)?)+")
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def extract_expression(text):
    """Pull a math expression like '12 * 4' out of a sentence, or None."""
    normalized = text.lower()
    for word, symbol in _MATH_WORDS:
        normalized = normalized.replace(word, f" {symbol} ")
    match = _EXPR_RE.search(normalized)
    return " ".join(match.group(0).split()) if match else None


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


def calculator(expression):
    """Evaluate a simple arithmetic expression safely (no eval())."""
    tree = ast.parse(expression, mode="eval")
    result = _safe_eval(tree.body)
    return result


# ---- Tool 2: mock trivia search ----------------------------------------


def _keywords(text):
    words = re.findall(r"[a-z]+", text.lower())
    return {w for w in words if w not in STOPWORDS}


def find_trivia_match(question):
    """Return the trivia key whose keywords overlap the question most, or None."""
    q_words = _keywords(question)
    if not q_words:
        return None
    best_key, best_score = None, 0
    for key in TRIVIA:
        score = len(q_words & _keywords(key))
        if score > best_score:
            best_key, best_score = key, score
    return best_key if best_score >= 2 else None


def search_trivia(query):
    """Look up the closest trivia fact, or say there isn't one."""
    match = find_trivia_match(query)
    if match:
        return TRIVIA[match]
    return "I don't have a trivia fact for that."


# ---- Default mode: rule-based routing -----------------------------------


def route(question):
    """Decide which tool (if any) a plain rule-based agent would use."""
    expr = extract_expression(question)
    if expr:
        return "calculator", expr
    if find_trivia_match(question):
        return "search_trivia", question
    return None, None


def run_rule_based(question):
    print("[THINKING] Checking whether this needs a tool...")
    tool, tool_input = route(question)

    if tool == "calculator":
        print(f'[TOOL CALL] calculator("{tool_input}")')
        result = calculator(tool_input)
        print(f"[TOOL RESULT] {result}")
        print(f"[FINAL ANSWER] {tool_input} = {result}")
    elif tool == "search_trivia":
        print(f'[TOOL CALL] search_trivia("{tool_input}")')
        result = search_trivia(tool_input)
        print(f"[TOOL RESULT] {result}")
        print(f"[FINAL ANSWER] {result}")
    else:
        print("[THINKING] No tool matches — not math, not one of my trivia topics.")
        print(
            "[FINAL ANSWER] I can only do math (e.g. \"12 * 4\") or answer a "
            "handful of trivia questions. Try one of those!"
        )


# ---- --key mode: a real function-calling loop ---------------------------

TOOL_SCHEMAS_ANTHROPIC = [
    {
        "name": "calculator",
        "description": "Evaluate a simple arithmetic expression like '12 * 4'.",
        "input_schema": {
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    },
    {
        "name": "search_trivia",
        "description": "Look up a fun trivia fact about topics like animals, "
        "mountains, planets, inventions.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]

TOOL_SCHEMAS_OPENAI = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a simple arithmetic expression like '12 * 4'.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_trivia",
            "description": "Look up a fun trivia fact about topics like animals, "
            "mountains, planets, inventions.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


def _execute_tool(name, tool_input):
    if name == "calculator":
        return str(calculator(tool_input["expression"]))
    if name == "search_trivia":
        return search_trivia(tool_input["query"])
    return f"Unknown tool: {name}"


def _post_json(url, payload, headers):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def run_with_anthropic(question, api_key):
    system = (
        "Briefly say what you're checking, then use a tool if the question "
        "needs one (math or trivia). If no tool fits, just answer directly."
    )
    messages = [{"role": "user", "content": question}]
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    data = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "model": "claude-3-5-haiku-latest",
            "max_tokens": 500,
            "system": system,
            "tools": TOOL_SCHEMAS_ANTHROPIC,
            "messages": messages,
        },
        headers,
    )

    for block in data["content"]:
        if block["type"] == "text" and block["text"].strip():
            print(f"[THINKING] {block['text'].strip()}")

    tool_uses = [b for b in data["content"] if b["type"] == "tool_use"]
    if not tool_uses:
        final_text = next(b["text"] for b in data["content"] if b["type"] == "text")
        print(f"[FINAL ANSWER] {final_text.strip()}")
        return

    messages.append({"role": "assistant", "content": data["content"]})
    tool_results = []
    for block in tool_uses:
        print(f'[TOOL CALL] {block["name"]}({json.dumps(block["input"])})')
        result = _execute_tool(block["name"], block["input"])
        print(f"[TOOL RESULT] {result}")
        tool_results.append(
            {"type": "tool_result", "tool_use_id": block["id"], "content": result}
        )
    messages.append({"role": "user", "content": tool_results})

    data = _post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "model": "claude-3-5-haiku-latest",
            "max_tokens": 500,
            "system": system,
            "tools": TOOL_SCHEMAS_ANTHROPIC,
            "messages": messages,
        },
        headers,
    )
    final_text = " ".join(
        b["text"] for b in data["content"] if b["type"] == "text"
    ).strip()
    print(f"[FINAL ANSWER] {final_text}")


def run_with_openai(question, api_key):
    system = (
        "Briefly say what you're checking, then use a tool if the question "
        "needs one (math or trivia). If no tool fits, just answer directly."
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question},
    ]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "content-type": "application/json",
    }

    data = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {"model": "gpt-4o-mini", "messages": messages, "tools": TOOL_SCHEMAS_OPENAI},
        headers,
    )
    msg = data["choices"][0]["message"]
    if msg.get("content"):
        print(f"[THINKING] {msg['content'].strip()}")

    tool_calls = msg.get("tool_calls")
    if not tool_calls:
        print(f"[FINAL ANSWER] {msg['content'].strip()}")
        return

    messages.append(msg)
    for call in tool_calls:
        name = call["function"]["name"]
        tool_input = json.loads(call["function"]["arguments"])
        print(f'[TOOL CALL] {name}({json.dumps(tool_input)})')
        result = _execute_tool(name, tool_input)
        print(f"[TOOL RESULT] {result}")
        messages.append(
            {"role": "tool", "tool_call_id": call["id"], "content": result}
        )

    data = _post_json(
        "https://api.openai.com/v1/chat/completions",
        {"model": "gpt-4o-mini", "messages": messages, "tools": TOOL_SCHEMAS_OPENAI},
        headers,
    )
    print(f"[FINAL ANSWER] {data['choices'][0]['message']['content'].strip()}")


def run_live(question):
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not anthropic_key and not openai_key:
        sys.exit(
            "No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
            "or run without --key for rule-based mode."
        )

    print("🔑 Live agent mode — the model itself decides which tool to use:\n")
    try:
        if anthropic_key:
            run_with_anthropic(question, anthropic_key)
        else:
            run_with_openai(question, openai_key)
    except urllib.error.URLError as exc:
        sys.exit(f"Could not reach the live API: {exc}")


def main():
    args = sys.argv[1:]
    use_key = "--key" in args
    args = [a for a in args if a != "--key"]

    if not args:
        sys.exit('Usage: python trace.py "your question here" [--key]')

    question = args[0]
    if use_key:
        run_live(question)
    else:
        print("📄 Rule-based mode — a regex decides which tool to use:\n")
        run_rule_based(question)
    print()


if __name__ == "__main__":
    main()
