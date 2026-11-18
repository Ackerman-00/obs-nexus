#!/usr/bin/env python3
"""Assert the scheduler gate and the external verifier parse the same contract."""
import pathlib
import re
import sys

wf = pathlib.Path(".github/workflows/opencode-schedule.yml").read_text()
ver = pathlib.Path("tools/verify-opensuse.sh").read_text()

patterns = [
    ("install-table parser", r'verdict = "FAIL"'),
    ("FAIL dominance", r'verdict == "EXTERNAL"'),
    ("EXTERNAL/GAP pairing", r"GAP: external"),
    ("dependency table header", r"upstream deps evidence"),
    ("deps row shape", r"deps-verified"),
    ("correctness contract", r"unproven:"),
    ("version table", r"packaged version"),
    ("GAP classifier", r"GAP\|HOLD"),
    ("probe token", r"\[probe:"),
    ("actionable fails", r"actionable"),
    ("defects-found", r"defects-found:"),
    ("defects-fixed", r"defects-fixed:"),
    ("hunt count", r"hunt:"),
    ("websearch date", r"websearch:"),
    ("changed token", r"changed:"),
    ("plan token", r"plan:"),
    ("deps token", r"deps:"),
    ("artifact token", r"artifact:"),
    ("improve token", r"improve:"),
    ("why token", r"why:"),
    ("owner wait ban", r"needs-owner"),
]

bad = []
for name, pat in patterns:
    rx = re.compile(pat)
    if not rx.search(wf):
        bad.append("gate missing " + name)
    if not rx.search(ver):
        bad.append("verifier missing " + name)

obs_tokens = [
    "spec-cleaner", "rpmlint", "zypper",
    "debian updater markers: 0", "DOCKER BATTLE TEST",
]
for tok in obs_tokens:
    if tok not in wf:
        bad.append("gate missing OBS evidence " + tok)
    if tok not in ver:
        bad.append("verifier missing OBS evidence " + tok)

if bad:
    print("FAIL gate/verifier drift:")
    for item in bad:
        print("  " + item)
    sys.exit(1)
print("OK   gate and verifier parse the same evidence contract")
