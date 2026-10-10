#!/usr/bin/env python3
"""Payload reconciliation for *-craft RPM-repack updaters.

Added 2026-10-10 after pdfcraft-0.5.0 shipped a new NOTICE plus a
usr/share/<pkg>/models OCR-data dir that spec %files / %install /
debian.rules did not cover, failing the Tumbleweed build with
"Installed (but unpackaged) file(s) found" (plus a disordered
.changes tripping "%changelog not in descending chronological order").

Usage:
    reconcile-payload.py <pkg> <payload.rpm|payload.deb> <spec> <changes> <debian.rules>

Exit 0 = every payload file is covered by spec %files, every new data
dir has %install + debian.rules copies, and the .changes order is
descending. Exit 1 = HOLD (prints the drift list; the caller must leave
the tree untouched).

RPM payloads are listed with `rpm -qlpv` (directories skipped:
unpackaged dirs are warnings, unpackaged files are errors). DEB
payloads are parsed with stdlib only (ar headers + tarfile; data.tar
must be .gz/.xz) so the guard also runs on tool-poor CI runners.
"""
import fnmatch
import io
import re
import subprocess
import sys
import tarfile
import datetime

STANDARD_SHARE_DIRS = ("applications", "icons", "metainfo", "mime", "doc")


def list_rpm(path):
    out = subprocess.run(["rpm", "-qlpv", path],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f"rpm -qlpv failed: {out.stderr.strip()}")
    files = []
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) < 8 or parts[0].startswith("d"):
            continue
        files.append(parts[-1])
    return files


def list_deb(path):
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"!<arch>\n":
        raise RuntimeError("not an ar archive")
    off, members = 8, {}
    while off + 60 <= len(data):
        head = data[off:off + 60]
        name = head[:16].decode("ascii").strip()
        try:
            size = int(head[48:58].decode("ascii").strip())
        except ValueError:
            break
        members[name] = data[off + 60:off + 60 + size]
        off += 60 + size + (size & 1)
    blob = None
    for cand in ("data.tar.gz", "data.tar.xz"):
        if cand in members:
            blob = members[cand]
            break
    if blob is None:
        found = sorted(members)
        raise RuntimeError(f"unsupported data.tar in {found} "
                           "(need .gz/.xz for stdlib parsing)")
    names = []
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as tar:
        for entry in tar:
            if entry.isfile():
                names.append("/" + entry.name.lstrip("./"))
    return names


def main():
    pkg, payload, spec_path, changes_path, rules_path = sys.argv[1:6]
    try:
        files = (list_rpm(payload) if payload.endswith(".rpm")
                 else list_deb(payload))
    except RuntimeError as exc:
        print(f"HOLD: cannot list payload: {exc}")
        return 1
    except FileNotFoundError as exc:
        print(f"HOLD: missing listing tool: {exc}")
        return 1

    pkg_dirs = set()
    for path in files:
        m = re.match(r"^/usr/share/([^/]+)/", path)
        if m and m.group(1) not in STANDARD_SHARE_DIRS:
            pkg_dirs.add(m.group(1))

    spec = open(spec_path).read()
    filesect = spec.split("%files", 1)[1].split("%changelog", 1)[0]
    patterns = []
    for line in filesect.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^%(doc|license|config\S*|dir)\s+", "", line)
        line = line.replace("%{_datadir}", "/usr/share")
        line = line.replace("%{_bindir}", "/usr/bin")
        patterns.append(line)

    problems = []
    for path in files:
        if not any(fnmatch.fnmatchcase(path, pat) for pat in patterns):
            problems.append(f"uncovered-file: {path}")

    installsect = spec.split("%install", 1)[1].split("%check", 1)[0]
    rules = open(rules_path).read()
    for dirname in sorted(pkg_dirs):
        if f"usr/share/{dirname}" not in installsect:
            problems.append(f"missing-%install-copy: usr/share/{dirname}")
        if f"usr/share/{dirname}" not in rules:
            problems.append(f"missing-debian.rules-copy: usr/share/{dirname}")
        if not any(p == f"/usr/share/{dirname}"
                   or p.rstrip("*").startswith(f"/usr/share/{dirname}/")
                   for p in patterns):
            problems.append(f"missing-%files-cover: /usr/share/{dirname}/")

    bins = sorted({f.split("/")[-1] for f in files
                   if f.startswith("/usr/bin/")})
    for binary in bins:
        if binary not in installsect:
            problems.append(f"missing-%install-binary: {binary}")

    months = {m: i + 1 for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}
    dates = []
    for line in open(changes_path):
        m = re.match(r"^\* \w+ (\w+) (\d+) (\d{4}) ", line)
        if m:
            dates.append(datetime.date(int(m.group(3)),
                                       months[m.group(1)], int(m.group(2))))
    if any(a < b for a, b in zip(dates, dates[1:])):
        problems.append(
            f"changes-not-descending: {[str(d) for d in dates]}")

    if problems:
        print(f"HOLD: {pkg} payload/spec drift ({len(problems)} items):")
        for item in problems:
            print(f"  {item}")
        return 1
    print(f"OK: {pkg} {len(files)} payload files covered, "
          f"{len(bins)} binaries, {len(pkg_dirs)} extra dirs, "
          "changes order ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
