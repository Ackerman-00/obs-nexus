#!/usr/bin/env python3
"""No scheduler env string may approach Linux MAX_ARG_STRLEN."""
import glob
import sys

import yaml

LIMIT = 128 * 1024
worst = (0, "")
for path in sorted(glob.glob(".github/workflows/*.yml")):
    doc = yaml.safe_load(open(path))
    for job in (doc.get("jobs") or {}).values():
        for step in job.get("steps") or []:
            for key, value in (step.get("env") or {}).items():
                if isinstance(value, str):
                    size = len(value.encode())
                    if size > worst[0]:
                        worst = (size, f"{path} {step.get('name', '?')} {key}")
if worst[0] >= LIMIT:
    print(f"FAIL {worst[1]} is {worst[0]} bytes, at/over the {LIMIT} MAX_ARG_STRLEN limit")
    sys.exit(1)
print(f"OK   largest scheduler env string {worst[1]} is {worst[0]} bytes (< {LIMIT})")
