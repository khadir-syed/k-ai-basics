# GPT-2's word lists, for the web pages

Demos 01 and 05 split text into tokens the way GPT-2 does. In a terminal,
they use the `transformers` library. In the browser, the pages use
[`gpt2.py`](gpt2.py), which rebuilds the same tokenizer with `tiktoken` from
GPT-2's own two word lists:

| File | What it is |
|---|---|
| `vocab.json` | Every one of GPT-2's 50,257 tokens and its ID number |
| `merges.txt` | The order in which GPT-2 glues letters into bigger tokens |

Both are copied unchanged from the [`gpt2`](https://huggingface.co/openai-community/gpt2)
model on Hugging Face, released by OpenAI under the MIT licence. `gpt2.py`
checks both files against their fingerprints, so a changed file is refused.

[`tokens.js`](tokens.js) loads it into the page and draws the tokens.
When a letter is cut into several tokens (a Hindi letter, an emoji), its
pieces are drawn together, with the letter they make underneath.

The browser only downloads these two files (about 1.5 MB) — never the
GPT-2 model itself, which is about 500 MB.
