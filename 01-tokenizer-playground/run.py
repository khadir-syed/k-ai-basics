"""Tokenizer Playground — see how GPT-2 breaks a sentence into tokens
and guesses what word might come next.
"""
import sys


def build_token_table(tokens):
    """tokens: list of (piece, id) -> formatted table string."""
    lines = [f"{'#':>3}  {'TOKEN':<20} {'ID':>8}"]
    lines.append("-" * 34)
    for i, (piece, token_id) in enumerate(tokens):
        shown = piece.replace("\n", "\\n")
        lines.append(f"{i:>3}  {shown:<20} {token_id:>8}")
    return "\n".join(lines)


def build_bar_chart(predictions, width=30):
    """predictions: list of (piece, probability) sorted high to low."""
    lines = []
    for piece, prob in predictions:
        bar = "#" * max(1, round(prob * width))
        pct = f"{prob * 100:5.1f}%"
        lines.append(f"{piece:<15} {bar} {pct}")
    return "\n".join(lines)


def load_model():
    """Downloads GPT-2 (~500MB) from Hugging Face on first run, then caches it."""
    try:
        from huggingface_hub.utils import logging as hf_logging
        from transformers import GPT2LMHeadModel, GPT2Tokenizer

        hf_logging.set_verbosity_error()
    except ImportError:
        sys.exit(
            "Missing packages. Run: pip install -r requirements.txt"
        )

    try:
        tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
        model = GPT2LMHeadModel.from_pretrained("gpt2")
    except Exception as exc:
        sys.exit(
            "Could not download the GPT-2 model. This demo needs an internet "
            "connection the first time you run it (the model is cached locally "
            f"after that).\n\nDetails: {exc}"
        )
    model.eval()
    return tokenizer, model


def run(sentence):
    tokenizer, model = load_model()  # exits with a friendly message if packages are missing
    import torch

    token_ids = tokenizer.encode(sentence)
    tokens = [(tokenizer.decode([tid]), tid) for tid in token_ids]

    print("\nYour sentence, split into tokens:\n")
    print(build_token_table(tokens))

    with torch.no_grad():
        input_ids = torch.tensor([token_ids])
        logits = model(input_ids).logits[0, -1]
        probs = torch.softmax(logits, dim=-1)
        top_probs, top_ids = torch.topk(probs, 5)

    predictions = [
        (tokenizer.decode([tid]).strip() or "<space>", p.item())
        for tid, p in zip(top_ids, top_probs)
    ]

    print("\nTop 5 guesses for the next token:\n")
    print(build_bar_chart(predictions))
    print()


def main():
    if len(sys.argv) < 2:
        sys.exit('Usage: python run.py "your sentence here"')
    run(sys.argv[1])


if __name__ == "__main__":
    main()
