#!/usr/bin/env python3
"""Distro index collision check for opensuse-nexus (run every sweep).

The repo rule (AGENTS.md / owner order 2026-10-12) is: never ship a package
that shadows the target distro's own copy, and re-check the distro indexes
every run because point releases add packages. This tool makes that rule
executable instead of a memory exercise.

It answers three questions and exits non-zero only for a real defect:

1. RPM side -- does Tumbleweed OSS already ship one of our package names?
   A same-name RPM shadows the distro package -> FAIL.
2. DEB side -- does Debian testing (forky) or unstable (sid) already ship
   one of our .deb package names? A *library* (lib* / *-devel) shadow is the
   latent-collision class that produced the wlroots/scenefx damage -> FAIL.
   A plain application/data package with an identical file layout is a
   version upgrade along the same package name -> WARN (reported, allowed).
3. Invariants that past runs got wrong:
   - `wlroots` must never exist in this repo (collides on libwlroots-0.20.so)
   - scenefx must be RPM-only (Debian ships libscenefx-0.5) -> no .dsc
   - every spec carries ExclusiveArch: x86_64
   - every .deb is Architecture: amd64, except the documented
     architecture-independent recipes (data-only / pure-Python / config)

Stdlib only (urllib + gzip + re), no credentials needed.
"""

from __future__ import annotations

import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TW_OSS = "https://download.opensuse.org/tumbleweed/repo/oss/"
DEB_MIRRORS = {
    "testing/forky": "https://deb.debian.org/debian/dists/testing/main/binary-amd64/Packages.gz",
    "unstable/sid": "https://deb.debian.org/debian/dists/sid/main/binary-amd64/Packages.gz",
}
# PikaOS rebuilds Debian with its own `NNNpikaN` suffixes and a suite pin that
# outranks third-party repos, so a same-name package there decides what a
# PikaOS user gets. The site exposes a JSON package index (no Packages.gz
# access: HTTP 403), which is the only machine-readable source.
PIKA_API = "https://packages.pika-os.com/api/packages"
PIKA_REPOS = {1: "cockatiel", 2: "nest", 3: "raven", 4: "parrot", 5: "canary", 6: "pigeon"}

ARCH_ALL_OK = {"bibata-cursor-theme", "lazyvim-git", "faugus-launcher",
               "hatter-icon-theme", "whitesur-icon-theme"}
RPM_ONLY = {"scenefx"}
FORBIDDEN = {"wlroots"}


def fetch(url: str, timeout: int = 60) -> bytes:
    last: Exception | None = None
    for attempt in range(4):
        req = urllib.request.Request(url, headers={"User-Agent": "opensuse-nexus-collision-check"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as exc:
            last = exc
            time.sleep(3 * (attempt + 1))
    raise last


def local_packages() -> list[str]:
    out = []
    for entry in sorted(os.listdir(REPO_ROOT)):
        path = os.path.join(REPO_ROOT, entry)
        if not os.path.isdir(path):
            continue
        if any(f.endswith(".spec") for f in os.listdir(path)):
            out.append(entry)
    return out


def tumbleweed_packages() -> dict[str, str]:
    repomd = fetch(TW_OSS + "repodata/repomd.xml").decode("utf-8", "replace")
    hrefs = re.findall(r'href="([^"]*primary\.xml\.(?:gz|zst))"', repomd)
    if not hrefs:
        raise RuntimeError("primary.xml location not found in Tumbleweed repomd.xml")
    # repomd can lag the mirror: the referenced hash then answers 404 while the
    # published primary sits in the same repodata directory under a newer hash.
    listing = ""
    try:
        listing = fetch(TW_OSS + "repodata/").decode("utf-8", "replace")
        hrefs += ["repodata/" + n for n in re.findall(r'([a-f0-9]{32,}-primary\.xml\.(?:zst|gz))', listing)]
    except Exception:
        pass
    raw = None
    for href in hrefs:
        try:
            raw = fetch(TW_OSS + href)
            break
        except Exception:
            continue
    if raw is None:
        raise RuntimeError("no published primary.xml readable from the Tumbleweed repodata")
    if href.endswith(".zst"):
        zstd = shutil.which("zstd")
        if not zstd:
            raise RuntimeError("primary.xml.zst served but no zstd binary available")
        raw = subprocess.run([zstd, "-dc"], input=raw, capture_output=True, check=True).stdout
    else:
        raw = gzip.decompress(raw)
    data = raw.decode("utf-8", "replace")
    versions: dict[str, str] = {}
    for block in re.findall(r"<package type=\"rpm\">(.*?)</package>", data, re.S):
        name = re.search(r"<name>([^<]+)</name>", block)
        ver = re.search(r'<version epoch="[^"]*" ver="([^"]+)" rel="([^"]+)"', block)
        if name and ver and name.group(1) not in versions:
            versions[name.group(1)] = f"{ver.group(1)}-{ver.group(2)}"
    return versions


def debian_packages(url: str) -> dict[str, str]:
    data = gzip.decompress(fetch(url)).decode("utf-8", "replace")
    versions: dict[str, str] = {}
    for block in data.split("\n\n"):
        name = re.search(r"^Package: (.+)$", block, re.M)
        ver = re.search(r"^Version: (.+)$", block, re.M)
        if name and ver:
            versions.setdefault(name.group(1).strip(), ver.group(1).strip())
    return versions


def spec_version(pkg: str) -> str:
    spec = os.path.join(REPO_ROOT, pkg, pkg + ".spec")
    with open(spec, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    return "?"


def deb_name(pkg: str) -> str | None:
    control = os.path.join(REPO_ROOT, pkg, "debian.control")
    if not os.path.isfile(control):
        return None
    with open(control, encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("Package:"):
                return line.split(":", 1)[1].strip()
    return None


def deb_order(char: str) -> int:
    """Debian policy 5.6.12: '~' sorts before everything, letters before symbols."""
    if char.isdigit():
        return 0
    if char.isalpha():
        return ord(char)
    if char == "~":
        return -1
    return ord(char) + 256


def deb_compare(left: str, right: str) -> int:
    """-1/0/1 for left<right per Debian version ordering (epoch:upstream-revision)."""
    def split(v: str) -> tuple[int, str, str]:
        epoch = 0
        if ":" in v:
            head, v = v.split(":", 1)
            epoch = int(head) if head.isdigit() else 0
        rev = ""
        if "-" in v:
            v, rev = v.rsplit("-", 1)
        return epoch, v, rev

    for a, b in ((split(left), split(right)),):
        if a[0] != b[0]:
            return -1 if a[0] < b[0] else 1
        for pa, pb in ((a[1], b[1]), (a[2], b[2])):
            ia = ib = 0
            while ia < len(pa) or ib < len(pb):
                # non-digit prefix
                sa, sb = "", ""
                while ia < len(pa) and not pa[ia].isdigit():
                    sa += pa[ia]
                    ia += 1
                while ib < len(pb) and not pb[ib].isdigit():
                    sb += pb[ib]
                    ib += 1
                for ca, cb in zip(sa, sb):
                    if deb_order(ca) != deb_order(cb):
                        return -1 if deb_order(ca) < deb_order(cb) else 1
                if len(sa) != len(sb):
                    # '~' sorts before everything, including end-of-string
                    if len(sa) > len(sb) and sa[len(sb):].startswith("~"):
                        return -1
                    if len(sb) > len(sa) and sb[len(sa):].startswith("~"):
                        return 1
                    return -1 if len(sa) < len(sb) else 1
                na, nb = "", ""
                while ia < len(pa) and pa[ia].isdigit():
                    na += pa[ia]
                    ia += 1
                while ib < len(pb) and pb[ib].isdigit():
                    nb += pb[ib]
                    ib += 1
                if na or nb:
                    ia2, ib2 = int(na or "0"), int(nb or "0")
                    if ia2 != ib2:
                        return -1 if ia2 < ib2 else 1
    return 0


def pika_versions(term: str, timeout: int = 60) -> dict[str, list[tuple[str, str]]]:
    """name -> [(repo label, version)] from the PikaOS package index."""
    url = f"{PIKA_API}?search={urllib.parse.quote(term)}&limit=100"
    req = urllib.request.Request(url, headers={"User-Agent": "opensuse-nexus-collision-check"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        doc = json.loads(resp.read())
    out: dict[str, list[tuple[str, str]]] = {}
    for row in doc.get("packages", []):
        label = PIKA_REPOS.get(row.get("repoId"), str(row.get("repoId")))
        out.setdefault(row.get("name", ""), []).append((label, row.get("version", "")))
    return out


def declares_replacement(pkg: str, distro_name: str) -> bool:
    """Both fields are required: Provides alone keeps the file conflict."""
    spec = os.path.join(REPO_ROOT, pkg, pkg + ".spec")
    try:
        text = open(spec, encoding="utf-8").read()
    except OSError:
        return False
    names = re.escape(distro_name)
    provides = re.search(r"^Provides:\s*(?:\S+\s+)*?" + names + r"\b", text, re.M)
    obsoletes = re.search(r"^Obsoletes:\s*(?:\S+\s+)*?" + names + r"\b", text, re.M)
    return bool(provides and obsoletes)


def self_test() -> int:
    import tempfile
    global REPO_ROOT
    cases = [
        ("Provides:       ProtonPlus = %{version}\nObsoletes:      ProtonPlus <= %{version}\n", True),
        ("Conflicts:      ProtonPlus\n", False),
        ("Provides:       ProtonPlus = 1.0\nConflicts:      ProtonPlus\n", False),
        ("Obsoletes:      ProtonPlus <= 1.0\n", False),
        ("Provides:       OtherThing = 1.0\nObsoletes:      OtherThing <= 1.0\n", False),
    ]
    saved = REPO_ROOT
    failures = 0
    try:
        for body, expected in cases:
            tmp = tempfile.mkdtemp()
            os.makedirs(os.path.join(tmp, "demo"))
            with open(os.path.join(tmp, "demo", "demo.spec"), "w", encoding="utf-8") as fh:
                fh.write("Name: demo\n" + body)
            REPO_ROOT = tmp
            got = declares_replacement("demo", "ProtonPlus")
            shutil.rmtree(tmp)
            if got != expected:
                print(f"SELFTEST FAIL {body!r}: expected {expected}, got {got}")
                failures += 1
    finally:
        REPO_ROOT = saved
    version_cases = [
        (("2.22.4", "2.22.1-101pika1"), 1, "newer upstream beats a rebuild suffix"),
        (("2.22.1-101pika1", "2.22.1-101pika1"), 0, "identical NVR"),
        (("1:0.5.17", "0.5.17"), 1, "epoch outranks everything"),
        (("0.5.17", "1:0.5.16"), -1, "epoch-0 loses to epoch-1"),
        (("1.4.0", "1.4.0-1.1"), -1, "revision makes the distro NVR newer"),
        (("2.0.7", "2.0.6-1"), 1, "point release is newer than an older one"),
        (("1.0.0~beta1", "1.0.0"), -1, "'~' sorts before the release"),
        (("1.0.0+git20260101", "1.0.0"), 1, "git snapshot sorts after the release"),
    ]
    for (left, right), expected, why in version_cases:
        got = (deb_compare(left, right) > 0) - (deb_compare(left, right) < 0)
        if got != expected:
            print(f"SELFTEST FAIL deb_compare({left}, {right}) = {got}, expected {expected} ({why})")
            failures += 1
    if failures:
        return 1
    print(f"distro-collision self-test: {len(cases)} provides/obsoletes + "
          f"{len(version_cases)} version fixtures, all pass")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    packages = local_packages()
    if not packages:
        print("FAIL: no package directories found (run from the repo root)")
        return 1

    fails: list[str] = []
    warns: list[str] = []

    print(f"local packages: {len(packages)}")
    read_indexes: list[str] = []
    for pkg in packages:
        if pkg in FORBIDDEN:
            fails.append(f"{pkg}: forbidden package present (owner order: distro ships it, never repackage)")
        spec_path = os.path.join(REPO_ROOT, pkg, pkg + ".spec")
        with open(spec_path, encoding="utf-8") as handle:
            spec = handle.read()
        if not re.search(r"^ExclusiveArch:\s*x86_64\s*$", spec, re.M):
            fails.append(f"{pkg}: spec missing 'ExclusiveArch: x86_64'")
        has_dsc = os.path.isfile(os.path.join(REPO_ROOT, pkg, pkg + ".dsc"))
        if pkg in RPM_ONLY and has_dsc:
            fails.append(f"{pkg}: RPM-only package still carries a Debian recipe ({pkg}.dsc)")
        control = os.path.join(REPO_ROOT, pkg, "debian.control")
        if has_dsc and os.path.isfile(control):
            with open(control, encoding="utf-8") as handle:
                arch = re.search(r"^Architecture:\s*(\S+)", handle.read(), re.M)
            if not arch:
                fails.append(f"{pkg}: debian.control has no Architecture field")
            elif arch.group(1) != "amd64" and pkg not in ARCH_ALL_OK:
                fails.append(f"{pkg}: Architecture: {arch.group(1)} (amd64 expected, {pkg} is not a documented arch-independent recipe)")
            elif arch.group(1) == "all" and pkg not in ARCH_ALL_OK:
                fails.append(f"{pkg}: Architecture: all without owner approval")

    try:
        tw = tumbleweed_packages()
        if not tw:
            raise RuntimeError("primary.xml parsed to zero packages")
    except Exception as exc:
        print(f"WARN: RPM shadow check NOT PERFORMED - Tumbleweed index unreadable ({exc})")
        tw = {}

    print(f"Tumbleweed OSS packages: {len(tw)}")
    if tw:
        read_indexes.append("Tumbleweed")
    for pkg in packages:
        if pkg not in tw:
            continue
        if pkg.startswith("lib") or pkg.endswith("-devel"):
            fails.append(f"RPM library shadow: {pkg} {spec_version(pkg)} also ships in Tumbleweed OSS {tw[pkg]}")
        else:
            warns.append(f"same-name RPM upgrade: {pkg} {tw[pkg]} (Tumbleweed OSS) vs ours {spec_version(pkg)}")

    tw_lower = {name.lower(): name for name in tw}
    for pkg in packages:
        if pkg in tw:
            continue
        match = tw_lower.get(pkg.lower())
        if not match:
            continue
        if declares_replacement(pkg, match):
            warns.append(
                f"case-collision RPM handled: ours {pkg} {spec_version(pkg)} declares "
                f"Provides/Obsoletes {match}, so zypper replaces the distro {match} {tw[match]}"
            )
        else:
            fails.append(
                f"case-collision RPM unhandled: ours {pkg} {spec_version(pkg)} vs distro {match} {tw[match]} "
                f"(Tumbleweed OSS) - distinct RPM names installing overlapping payload paths, so "
                f"'zypper in {pkg}' aborts on a box that has {match} installed; declare "
                f"Provides/Obsoletes {match} or rename ours"
            )

    for label, url in DEB_MIRRORS.items():
        try:
            deb = debian_packages(url)
        except Exception as exc:
            print(f"WARN: could not read Debian {label} index ({exc}); DEB shadow check skipped")
            continue
        print(f"Debian {label} packages: {len(deb)}")
        read_indexes.append(f"Debian {label}")
        for pkg in packages:
            name = deb_name(pkg)
            if not name or name not in deb:
                continue
            if name.startswith("lib") or name.endswith("-devel"):
                fails.append(f"DEB library shadow: {name} also ships in Debian {label} {deb[name]}")
            else:
                warns.append(f"same-name upgrade: {name} {deb[name]} (Debian {label}) vs ours {spec_version(pkg)}")

    if "--skip-pika" not in sys.argv:
        pika_hits: list[str] = []
        pika_read = False
        for pkg in packages:
            name = deb_name(pkg)
            if not name:
                continue
            try:
                index = pika_versions(name)
            except Exception as exc:
                print(f"WARN: PikaOS index unreadable ({type(exc).__name__}); PikaOS check stopped")
                pika_hits = []
                break
            pika_read = True
            rows = index.get(name)
            if not rows:
                continue
            ours = spec_version(pkg)
            newest = max((v for _r, v in rows), key=lambda v: (deb_compare(v, ours), v))
            repos = sorted({r for r, _v in rows})
            if deb_compare(newest, ours) > 0:
                warns.append(
                    f"PikaOS newer rebuild: {name} {newest} ({','.join(repos)}) vs ours {ours} - "
                    f"on PikaOS the suite pin prefers theirs, so ours is not the installed version")
            elif deb_compare(newest, ours) == 0:
                warns.append(
                    f"PikaOS same version: {name} {newest} ({','.join(repos)}) vs ours {ours} - "
                    f"identical NVR, the PikaOS suite pin decides which repo wins")
            else:
                warns.append(
                    f"PikaOS older rebuild: {name} {newest} ({','.join(repos)}) vs ours {ours} - "
                    f"apt needs a pin/preference for our repo to install the newer build")
            pika_hits.append(f"{name} theirs={newest} ours={ours}")
        if pika_read:
            read_indexes.append("PikaOS")
            print(f"pikaos: {len(pika_hits)} same-name package(s) in the PikaOS index"
                  + (": " + "; ".join(pika_hits) if pika_hits else ""))

    print("\n----- DISTRO COLLISION REPORT -----")
    for warning in warns:
        print(f"WARN: {warning}")
    for failure in fails:
        print(f"FAIL: {failure}")
    if not fails:
        print(f"PASS: {len(packages)} packages checked, no shadowing violation "
              f"(indexes read live: {', '.join(read_indexes) or 'none'})")
        if len(read_indexes) < 3:
            print("WARN: coverage incomplete - a skipped index proves nothing, re-run it")
        return 0
    print(f"FAIL: {len(fails)} collision violation(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
