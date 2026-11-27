#!/usr/bin/env python3
"""Turn install-sweep rows into the relay install-test table, FAIL cells intact."""
import argparse
import glob
import os
import re
import sys

TARGETS = ("tumbleweed", "testing", "sid")
COLS = {
    "tumbleweed": "zypper install test (TW)",
    "testing": "deb install test (Testing)",
    "sid": "deb install test (Sid)",
}


def parse_rows(text):
    rows = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 3:
            continue
        pkg, target, verdict = cells
        if pkg == "package" or target not in TARGETS:
            continue
        if verdict not in ("PASS", "FAIL", "HARNESS"):
            continue
        rows.setdefault(pkg, {})[target] = verdict
    return rows


def log_facts(path):
    """markers/stamp_bad/ldd_missing/smoke_rc as observed by the probe."""
    facts = {}
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return facts
    for key in ("markers", "stamp_bad", "ldd_missing", "smoke_rc"):
        m = re.search(r"^%s=(\d+)$" % key, text, re.M)
        if m:
            facts[key] = int(m.group(1))
    return facts


def status_of(verdicts, facts):
    vals = list(verdicts.values())
    if "FAIL" in vals:
        return "broken-(install)"
    if "HARNESS" in vals:
        return "blocked-(harness)"
    if facts.get("smoke_rc", 0) != 0:
        return "broken-(smoke)"
    if facts.get("ldd_missing", 0) != 0:
        return "broken-(ldd)"
    if len(vals) == len(TARGETS):
        return "installable"
    return "installable-partial"


def table(rows, logdir):
    out = ["| package | OBS build | zypper install test (TW) | deb install test (Testing) | deb install test (Sid) | smoke test | status |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    counts = {"PASS": 0, "FAIL": 0, "HARNESS": 0}
    for pkg in sorted(rows):
        v = rows[pkg]
        for val in v.values():
            counts[val] = counts.get(val, 0) + 1
        facts = log_facts(os.path.join(logdir, pkg + "-tumbleweed.log"))
        if not facts:
            smoke = "not-run"
        elif "smoke_rc" not in facts:
            smoke = "skipped-(files-only)"
        else:
            smoke = "PASS" if facts["smoke_rc"] == 0 else "FAIL"
        cells = [v.get(t, "not-run") for t in TARGETS]
        out.append("| %s | succeeded | %s | %s | %s | %s | %s |"
                   % (pkg, cells[0], cells[1], cells[2], smoke, status_of(v, facts)))
    return out, counts


def selftest():
    ok = True
    sample = "| alpha | tumbleweed | PASS |\n| alpha | testing | PASS |\n| alpha | sid | FAIL |\n"
    rows = parse_rows(sample)
    t, counts = table(rows, "/nonexistent")
    if counts["FAIL"] != 1 or "broken-(install)" not in t[-1]:
        print("FAIL: FAIL cell not propagated"); ok = False
    rows2 = parse_rows("| beta | tumbleweed | PASS |\n| beta | testing | HARNESS |\n")
    t2, _ = table(rows2, "/nonexistent")
    if "blocked-(harness)" not in t2[-1]:
        print("FAIL: HARNESS not surfaced"); ok = False
    if "not-run" not in t2[-1]:
        print("FAIL: missing target not marked"); ok = False
    print("install-table selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", default="/tmp/opencode/install-sweep/rows.txt")
    ap.add_argument("--logs", default="/tmp/opencode/install-sweep")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not os.path.exists(args.rows):
        print("no rows file:", args.rows, file=sys.stderr)
        return 2
    rows = parse_rows(open(args.rows, encoding="utf-8", errors="replace").read())
    lines, counts = table(rows, args.logs)
    print("\n".join(lines))
    print("install-table: %d packages, %d PASS, %d FAIL, %d HARNESS"
          % (len(rows), counts["PASS"], counts["FAIL"], counts["HARNESS"]))
    return 1 if counts["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
