"""Self-check for tool logic and rule-based routing. Runs instantly, no
network calls. Run with: python test_trace.py
"""
from trace import calculator, extract_expression, route, search_trivia

# calculator
assert extract_expression("what is 12 times 4") == "12 * 4"
assert extract_expression("7 plus 5") == "7 + 5"
assert extract_expression("hello there") is None
assert calculator("12 * 4") == 48
assert calculator("7 + 5") == 12

# trivia search
answer = search_trivia("how many moons does jupiter have")
assert "95" in answer
assert "don't have" in search_trivia("what color is the sky")

# routing
tool, tool_input = route("what is 6 * 7")
assert tool == "calculator" and tool_input == "6 * 7"

tool, tool_input = route("what is the fastest land animal")
assert tool == "search_trivia"

tool, tool_input = route("tell me a joke")
assert tool is None

print("All checks passed.")
