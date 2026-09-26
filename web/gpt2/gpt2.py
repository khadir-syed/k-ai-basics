"""GPT-2's tokenizer for the web pages (Demos 01 and 05).

The terminal demos split text with GPT-2's tokenizer from `transformers`,
which is too big for a browser. The web pages use `tiktoken` instead (it's
in Pyodide), built from GPT-2's own two word lists, kept next to this file:
vocab.json and merges.txt, copied unchanged from the "gpt2" model on Hugging
Face. Same word lists, same splitting rule, so the same tokens — and each
page re-checks that live against examples made by the terminal version.
"""
import os

import tiktoken
from tiktoken.load import data_gym_to_mergeable_bpe_ranks
from tiktoken_ext.openai_public import r50k_pat_str

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    ranks = data_gym_to_mergeable_bpe_ranks(
        vocab_bpe_file=os.path.join(HERE, "merges.txt"),
        encoder_json_file=os.path.join(HERE, "vocab.json"),
        # The files' fingerprints: tiktoken refuses them if they were changed.
        vocab_bpe_hash="1ce1664773c50f3e0cc8842619a93edc4624525b728b188a9e0be33b7726adc5",
        encoder_json_hash="196139668be63f3b5d6574427317ae82f612a97c5d1cdaf36ed2256dbf636783",
    )
    return tiktoken.Encoding(
        name="gpt2",
        explicit_n_vocab=50257,
        pat_str=r50k_pat_str,
        mergeable_ranks=ranks,
        special_tokens={"<|endoftext|>": 50256},
    )


class Tokenizer:
    """Just the two things the demos use: encode() and decode()."""

    def __init__(self):
        self.enc = load()

    def encode(self, text):
        # Like the terminal version: typing "<|endoftext|>" gives GPT-2's one
        # special "end of text" token (tiktoken would refuse it otherwise).
        return self.enc.encode(text, allowed_special="all")

    def decode(self, ids):
        return self.enc.decode(ids)

    def pieces(self, text):
        """The tokens of text, as (piece, id) pairs — like Demo 01's table — but
        grouped when a letter is cut across several tokens (a Hindi letter, an
        emoji), because a piece of a letter can't be shown on its own.

        Returns a list of (letter, [(piece, id), ...]); letter is None when the
        token holds whole letters by itself, else what the group spells.
        """
        groups, ids, raw = [], [], b""
        for token in self.encode(text):
            ids.append(token)
            raw += self.enc.decode_single_token_bytes(token)
            try:
                letter = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue  # still in the middle of a letter
            groups.append((letter if len(ids) > 1 else None, [(self.decode([i]), i) for i in ids]))
            ids, raw = [], b""
        if ids:  # the text itself ended mid-letter
            groups.append((None, [(self.decode([i]), i) for i in ids]))
        return groups
