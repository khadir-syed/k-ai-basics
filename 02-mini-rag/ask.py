"""Mini-RAG in a Terminal — chop story files into paragraphs, find the ones
that best match your question, and show you why.
"""
import glob
import json
import os
import sys
import urllib.error
import urllib.request

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")


def load_chunks(docs_dir=DOCS_DIR):
    """Read every .txt file in docs_dir, split each into paragraphs.

    Returns a list of (source_filename, chunk_text) tuples.
    """
    chunks = []
    for path in sorted(glob.glob(os.path.join(docs_dir, "*.txt"))):
        text = open(path, encoding="utf-8").read()
        for para in text.split("\n\n"):
            para = " ".join(para.split())  # collapse whitespace/newlines
            if para:
                chunks.append((os.path.basename(path), para))
    return chunks


def rank_chunks(question, chunks, top_n=5):
    """Rank chunks by TF-IDF cosine similarity to the question.

    Returns a list of (source, text, score) sorted highest score first.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    texts = [c[1] for c in chunks]
    vectorizer = TfidfVectorizer(stop_words="english")
    doc_vectors = vectorizer.fit_transform(texts)
    query_vector = vectorizer.transform([question])

    scores = cosine_similarity(query_vector, doc_vectors)[0]
    ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)

    return [(src, text, score) for (src, text), score in ranked[:top_n]]


def build_bar_chart(results, width=20):
    """results: list of (source, text, score) -> formatted string."""
    lines = []
    for source, text, score in results:
        bar = "#" * max(1, round(score * width))
        pct = f"{score * 100:5.1f}%"
        snippet = text if len(text) <= 70 else text[:67] + "..."
        lines.append(f"{source:<24} {bar:<{width}} {pct}\n    {snippet}")
    return "\n".join(lines)


def call_live_api(question, context):
    """Send context + question to Anthropic or OpenAI. Returns the answer text."""
    prompt = (
        "Answer the question using only the context below. "
        "If the context doesn't contain the answer, say so.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )

    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if anthropic_key:
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({
                "model": "claude-3-5-haiku-latest",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            }).encode(),
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["content"][0]["text"].strip()

    if openai_key:
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps({
                "model": "gpt-4o-mini",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            }).encode(),
            headers={
                "Authorization": f"Bearer {openai_key}",
                "content-type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()

    return None


def run(question, use_key=False):
    chunks = load_chunks()
    if not chunks:
        sys.exit(f"No .txt files found in {DOCS_DIR}")

    results = rank_chunks(question, chunks)

    print("\nTop 5 story paragraphs that best match your question:\n")
    print(build_bar_chart(results))

    if not use_key:
        print("\n📄 Retrieval-only mode — showing the best-matching paragraph as the answer:\n")
        print(results[0][1])
        print()
        return

    context = "\n\n".join(text for _, text, _ in results)
    try:
        answer = call_live_api(question, context)
    except urllib.error.URLError as exc:
        sys.exit(f"Could not reach the live API: {exc}")

    if answer is None:
        sys.exit(
            "No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY, "
            "or run without --key for retrieval-only mode."
        )

    print("\n🔑 Generated with live API:\n")
    print(answer)
    print()


def main():
    args = sys.argv[1:]
    use_key = "--key" in args
    args = [a for a in args if a != "--key"]

    if not args:
        sys.exit('Usage: python ask.py "your question here" [--key]')

    run(args[0], use_key=use_key)


if __name__ == "__main__":
    main()
