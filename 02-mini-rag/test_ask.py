"""Self-check for chunking and ranking logic. Runs instantly, no downloads.
Run with: python test_ask.py
"""
from ask import build_bar_chart, load_chunks, rank_chunks

chunks = load_chunks()
assert len(chunks) > 0, "expected at least one paragraph loaded from docs/"
assert all(isinstance(c[0], str) and isinstance(c[1], str) for c in chunks)

results = rank_chunks("Why did the wolf blow the house down?", chunks, top_n=5)
assert len(results) == 5
assert results[0][2] >= results[-1][2], "results should be sorted highest score first"
assert "three_little_pigs.txt" == results[0][0], "top match should come from the pigs story"

# A question sharing no words with any story scores exactly 0.
assert rank_chunks("tax rules for crypto", chunks)[0][2] == 0

chart = build_bar_chart(results[:2])
assert "#" in chart
assert "%" in chart

print("All checks passed.")
