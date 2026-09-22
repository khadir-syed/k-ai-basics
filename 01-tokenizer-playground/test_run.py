"""Self-check for the formatting logic. Runs instantly, no model download.
Run with: python test_run.py
"""
from run import build_token_table, build_bar_chart

table = build_token_table([("Hello", 15496), (",", 11), (" world", 995)])
assert "Hello" in table
assert "15496" in table
assert table.count("\n") == 2 + 3 - 1  # header + separator + 3 rows

chart = build_bar_chart([("cat", 0.5), ("dog", 0.25)])
assert "cat" in chart and "dog" in chart
assert "50.0%" in chart
assert chart.split("\n")[0].count("#") == 15  # 0.5 * width(30) = 15 bars

print("All checks passed.")
