"""Checks that every demo's copy of llm.py is byte-for-byte identical.

Each demo keeps its own copy so the folder works on its own; this makes sure
a fix in one copy never gets forgotten in the others. Run: python check_llm_copies.py
"""
import glob
import os
import sys

root = os.path.dirname(os.path.abspath(__file__))
copies = sorted(glob.glob(os.path.join(root, "*", "llm.py")))
if not copies:
    sys.exit("No llm.py copies found.")

contents = {path: open(path, "rb").read() for path in copies}
reference = contents[copies[0]]
different = [p for p in copies if contents[p] != reference]

for p in copies:
    mark = "✗ DIFFERENT" if contents[p] != reference else "✓"
    print(f"{mark:12} {os.path.relpath(p, root)}")

if different:
    sys.exit(f"\n{len(different)} copy/copies differ from "
             f"{os.path.relpath(copies[0], root)}. Make them identical.")
print(f"\nAll {len(copies)} copies of llm.py are identical.")
