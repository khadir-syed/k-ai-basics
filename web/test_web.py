"""Self-check for the web page: every example shown on web/index.html must be
exactly what the real demo code produces. Runs instantly, no network.
Run from the repo root with: python web/test_web.py
"""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "09-pii-redaction"))
from redact import redact  # noqa: E402

page = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()

examples = re.findall(r'<code class="ex-in">(.*?)</code>.*?<code class="ex-out[^"]*">(.*?)</code>', page, re.S)
assert len(examples) == 6, len(examples)
for shown_in, shown_out in examples:
    written, sees = html.unescape(shown_in), html.unescape(shown_out)
    assert redact(written)[0] == sees, (written, redact(written)[0], sees)

# Each ✅/❌ verdict matches what actually happened.
verdicts = re.findall(r'class="ex-why (caught|missed)"', page)
for (shown_in, _), verdict in zip(examples, verdicts):
    hidden = redact(html.unescape(shown_in))[0] != html.unescape(shown_in)
    assert (verdict == "caught") == hidden, (shown_in, verdict)

# The tap-to-try buttons offer exactly the same 6 examples.
chips = [html.unescape(c) for c in re.findall(r'data-try="(.*?)"', page)]
assert chips == [html.unescape(i) for i, _ in examples], chips

print("All checks passed.")
