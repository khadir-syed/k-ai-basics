"""Hallucination Demo — the same question, answered two ways: with no documents
(so a model would have to guess) and with documents looked up first (RAG).
"""
import argparse
import glob
import os
import sys
import urllib.error

import llm

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")

# A paragraph must match at least this well to count as "found". Below this,
# the match is usually just one everyday word in common, not a real answer.
THRESHOLD = 0.10


def load_chunks(docs_dir=DOCS_DIR):
    """Read every .txt file in docs_dir, split each into paragraphs.

    Returns a list of (source_filename, chunk_text) tuples.
    """
    chunks = []
    for path in sorted(glob.glob(os.path.join(docs_dir, "*.txt"))):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        for para in text.split("\n\n"):
            para = " ".join(para.split())  # collapse whitespace/newlines
            if para:
                chunks.append((os.path.basename(path), para))
    return chunks


def rank_chunks(question, chunks, top_n=3):
    """Rank chunks by TF-IDF cosine similarity to the question.

    Returns a list of (source, text, score) sorted highest score first.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        sys.exit("Missing packages. Run: pip install -r requirements.txt")

    texts = [c[1] for c in chunks]
    vectorizer = TfidfVectorizer(stop_words="english")
    doc_vectors = vectorizer.fit_transform(texts)
    query_vector = vectorizer.transform([question])

    scores = cosine_similarity(query_vector, doc_vectors)[0]
    ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)
    return [(src, text, score) for (src, text), score in ranked[:top_n]]


def found(results):
    """Only the results that match well enough to count as real evidence."""
    return [r for r in results if r[2] >= THRESHOLD]


def show_matches(results):
    if results[0][2] == 0:
        print("   (no paragraph shares a single word with your question)")
        return
    for source, text, score in results:
        bar = "#" * round(score * 20)
        mark = "✓" if score >= THRESHOLD else "✗ too weak"
        print(f"   {source:<26} {bar:<20} {score * 100:5.1f}%  {mark}")


# Both sides get the same length instruction, so the documents are the only
# real difference between them (and long answers don't get cut off).
LENGTH = "Answer in 2-3 sentences."


def ungrounded_prompt(question):
    return f"{LENGTH}\n\nQuestion: {question}"


def grounded_prompt(question, evidence):
    context = "\n\n".join(text for _, text, _ in evidence) or "(no matching documents)"
    return (
        f"{LENGTH} Use only the context below. "
        "If the context doesn't contain the answer, say you don't know.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )


def live_answer(prompt):
    try:
        answer = llm.ask(prompt, max_tokens=1000)  # room for "thinking" models
    except urllib.error.URLError as exc:
        sys.exit(f"The live API call failed (check your key and internet): {exc}")
    return answer or ("(The model sent back no words — it may have used all its room "
                      "thinking. Try a different model.)")


def run(question, use_key=False):
    chunks = load_chunks()
    if not chunks:
        sys.exit(f"No .txt files found in {DOCS_DIR}")
    results = rank_chunks(question, chunks)
    evidence = found(results)

    print(f'\n[QUESTION] "{question}"\n')

    print("── 1. WITHOUT DOCUMENTS ──────────────────────────────────────")
    if use_key:
        print("🔑 Live answer from a real model, given only your question:\n")
        print(live_answer(ungrounded_prompt(question)))
    else:
        print("🤷 Nothing to look at. A model with no documents has never read about")
        print("   this, so it would have to guess here — and a guess can sound just")
        print("   as sure as a fact.")
        print("📄 Illustrative — no AI was asked. Add --key to ask a real one.")

    print("\n── 2. WITH DOCUMENTS (look it up first) ──────────────────────")
    print("Best-matching paragraphs:")
    show_matches(results)
    print()

    if use_key:
        print(f"🔑 Live answer from the same model, given {len(evidence)} matching "
              "paragraph(s):\n")
        print(live_answer(grounded_prompt(question, evidence)))
    elif evidence:
        source, text, score = evidence[0]
        print(f"📚 Best evidence, from {source} ({score * 100:.1f}% match):\n")
        print(f"   {text}")
        print("\n   A model would answer from this. Word matching isn't perfect,")
        print("   so check it really answers your question!")
    else:
        print(f"🔍 Nothing matched well enough (need {THRESHOLD:.0%}). The honest")
        print("   answer here is: \"I don't know.\"")
    print()


def main():
    parser = argparse.ArgumentParser(description="Hallucination Demo")
    parser.add_argument("question", help="your question, in quotes")
    parser.add_argument("--key", action="store_true",
                        help="ask a real AI model both ways (needs an API key)")
    args = parser.parse_args()

    if args.key and not llm.has_key():
        sys.exit("No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
                 "or run without --key.")
    run(args.question, use_key=args.key)


if __name__ == "__main__":
    main()
