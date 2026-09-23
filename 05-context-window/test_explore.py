"""Self-check for the sliding-window logic. Runs instantly, no downloads.
Run with: python test_explore.py
"""
from explore import add_message, fill_bar

window = []
assert add_message(window, "a", 20, 50) == []
assert add_message(window, "b", 20, 50) == []
assert [t for t, _ in window] == ["a", "b"]

# Going over budget drops the OLDEST message first.
assert add_message(window, "c", 20, 50) == [("a", 20)]
assert [t for t, _ in window] == ["b", "c"]

# A big message can push out more than one old message.
assert add_message(window, "d", 45, 50) == [("b", 20), ("c", 20)]
assert window == [("d", 45)]

# A message bigger than the whole budget is refused and changes nothing.
assert add_message(window, "huge", 51, 50) is None
assert window == [("d", 45)]

assert fill_bar(0, 50) == "[" + "." * 20 + "]"
assert fill_bar(50, 50) == "[" + "#" * 20 + "]"
assert fill_bar(25, 50).count("#") == 10

print("All checks passed.")
