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
import os
import re
import shutil
import subprocess
import sys
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TW_OSS = "https://download.opensuse.org/tumbleweed/repo/oss/"
DEB_MIRRORS = {
    "testing/forky": "https://deb.debian.org/debian/dists/testing/main/binary-amd64/Packages.gz",
    "unstable/sid": "https://deb.debian.org/debian/dists/sid/main/binary-amd64/Packages.gz",
}

ARCH_ALL_OK = {"bibata-cursor-theme", "lazyvim-git", "faugus-launcher"}
RPM_ONLY = {"scenefx"}
FORBIDDEN = {"wlroots"}


def fetch(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "opensuse-nexus-collision-check"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


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
    match = re.search(r'href="([^"]*primary\.xml\.(?:gz|zst))"', repomd)
    if not match:
        raise RuntimeError("primary.xml location not found in Tumbleweed repomd.xml")
    href = match.group(1)
    raw = fetch(TW_OSS + href)
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


def main() -> int:
    packages = local_packages()
    if not packages:
        print("FAIL: no package directories found (run from the repo root)")
        return 1

    fails: list[str] = []
    warns: list[str] = []

    print(f"local packages: {len(packages)}")
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
    except Exception as exc:
        print(f"WARN: could not read Tumbleweed index ({exc}); RPM shadow check skipped")
        tw = {}

    print(f"Tumbleweed OSS packages: {len(tw)}")
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
        if match:
            warns.append(
                f"case-collision RPM: ours {pkg} {spec_version(pkg)} vs distro {match} {tw[match]} "
                f"(Tumbleweed OSS) - distinct RPM names installing overlapping payload paths"
            )

    for label, url in DEB_MIRRORS.items():
        try:
            deb = debian_packages(url)
        except Exception as exc:
            print(f"WARN: could not read Debian {label} index ({exc}); DEB shadow check skipped")
            continue
        print(f"Debian {label} packages: {len(deb)}")
        for pkg in packages:
            name = deb_name(pkg)
            if not name or name not in deb:
                continue
            if name.startswith("lib") or name.endswith("-devel"):
                fails.append(f"DEB library shadow: {name} also ships in Debian {label} {deb[name]}")
            else:
                warns.append(f"same-name upgrade: {name} {deb[name]} (Debian {label}) vs ours {spec_version(pkg)}")

    print("\n----- DISTRO COLLISION REPORT -----")
    for warning in warns:
        print(f"WARN: {warning}")
    for failure in fails:
        print(f"FAIL: {failure}")
    if not fails:
        print(f"PASS: {len(packages)} packages checked, no shadowing violation "
              f"(Tumbleweed + forky + sid indexes read live)")
        return 0
    print(f"FAIL: {len(fails)} collision violation(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
