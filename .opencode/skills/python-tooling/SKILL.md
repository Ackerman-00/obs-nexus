---
name: python-tooling
description: Standards for this repo's stdlib-only Python tools: positive and negative tests, no new runtime dependencies.
---

Tools under tools/ use the Python standard library only. Every detector needs
a positive fixture (must pass) and a negative fixture (must fail), and a shape
change to the relay contract needs a new negative case in tools/test-verifier.sh.
Keep comments short `# topic` labels. Never parse untrusted relay text with
eval; use regex and explicit field extraction. Run `python3 -m py_compile`.
