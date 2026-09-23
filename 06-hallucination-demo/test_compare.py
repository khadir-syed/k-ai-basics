"""Self-check for retrieval and the "found" cut-off. Runs instantly, no network.
Run with: python test_compare.py
"""
from compare import (THRESHOLD, found, grounded_prompt, load_chunks, rank_chunks,
                     ungrounded_prompt)

chunks = load_chunks()
assert len(chunks) == 10, len(chunks)  # 4 + 3 + 3 paragraphs

# Questions the documents can answer: top match from the right file, above the cut-off.
for question, source, answer in [
    ("What is the name of the mayor's cat in Puddlewick?", "puddlewick_town.txt", "Sir Pickles"),
    ("What year was the Puddlewick lighthouse built?", "puddlewick_lighthouse.txt", "1887"),
    ("Who won the Golden Welly last year?", "puddlewick_festival.txt", "Tilly Marsh"),
]:
    results = rank_chunks(question, chunks)
    assert results[0][0] == source, (question, results[0][0])
    assert answer in results[0][1], (question, results[0][1])
    assert results[0][2] >= THRESHOLD, (question, results[0][2])
    assert results == sorted(results, key=lambda r: r[2], reverse=True)

# A question the documents know nothing about: nothing counts as found.
assert found(rank_chunks("What are the tax rules for crypto?", chunks)) == []

# found() keeps only results at or above the cut-off.
assert found([("a", "x", 0.5), ("b", "y", THRESHOLD), ("c", "z", 0.05)]) == [
    ("a", "x", 0.5), ("b", "y", THRESHOLD)]

# Both sides get the same length instruction; only side 2 gets documents.
evidence = [("puddlewick_town.txt", "The mayor's cat is Sir Pickles.", 0.5)]
side1 = ungrounded_prompt("Who is the cat?")
side2 = grounded_prompt("Who is the cat?", evidence)
assert "2-3 sentences" in side1 and "2-3 sentences" in side2
assert "Sir Pickles" in side2 and "Sir Pickles" not in side1
assert "(no matching documents)" in grounded_prompt("Who is the cat?", [])

print("All checks passed.")
