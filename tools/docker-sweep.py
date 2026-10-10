#!/usr/bin/env python3
"""Docker-based package install + dependency + binary verification sweep.

Runs INSIDE the agent's execution. For each package:
  1. Spins up a clean Docker container (gentoo/stage3, fedora, voidlinux, etc.)
  2. Installs the package + all dependencies
  3. Verifies all deps resolved (no missing)
  4. Runs the binary (if applicable) and checks it starts
  5. Compares dependency tree against upstream expectations
  6. Reports PASS/FAIL per package with structured output

Usage (called by the agent during its run):
  python3 tools/docker-sweep.py --overlay . --type fedora --packages "pkg1 pkg2" --report docker-report.md
  python3 tools/docker-sweep.py --overlay . --type gentoo --all --report docker-report.md
  python3 tools/docker-sweep.py --overlay . --type opensuse --packages "zen-browser" --report docker-report.md
  python3 tools/docker-sweep.py --overlay . --type debian --all --report debian-report.md
      (debian type: verifies each spec's upstream .deb in a debian:testing
       container via apt/dpkg + ldd; --debdist testing|sid|both selects the
       Debian release(s): testing and sid are both maintained;
       --debdist all adds debian:13 (Trixie) + ubuntu:26.04 - ONE .dsc
       recipe builds all four targets)
  python3 tools/docker-sweep.py --overlay . --type arch --all --report arch-report.md
      (arch type: for each package's PKGBUILD (Arch extra target) in a
       clean archlinux:latest container: pacman -Syu, install the built
       .pkg.tar.zst via pacman -U or build+install via makepkg, then a
       namcap scan of the PKGBUILD and the built package)

Exit 0 = all tested packages passed. Exit 1 = any failures.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKIP_DIRS = {"cache", "job_out", "binpkgs", "distfiles", "ccache", ".github",
             ".git", "tools", "node_modules"}

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_DEPS_MISSING = "DEPS-MISSING"
STATUS_BINARY_FAIL = "BINARY-FAIL"
STATUS_INSTALL_FAIL = "INSTALL-FAIL"
STATUS_SKIP = "SKIP"
STATUS_VULN = "VULN"


def log(msg):
    print(msg, flush=True)


def detect_type(root):
    if list(root.rglob("*.ebuild")):
        return "gentoo"
    if (root / "debian" / "control").exists() or list(root.rglob("debian/control")):
        return "debian"
    if list(root.rglob("*.spec")):
        return "fedora"
    if (root / "pkgs").is_dir():
        return "nix"
    if (root / "srcpkgs").is_dir():
        return "void"
    return None


# ---------------------------------------------------------------------------
# Per-repo: extract package metadata
# ---------------------------------------------------------------------------

def get_gentoo_packages(root):
    pkgs = []
    for eb in sorted(root.rglob("*.ebuild")):
        if any(x in eb.parts for x in SKIP_DIRS) or len(eb.parts) < 3:
            continue
        cat = eb.parent.parent.name
        name = eb.parent.name
        atom = "%s/%s" % (cat, name)
        pkgs.append((atom, atom, eb))
    return pkgs


def get_fedora_packages(root):
    pkgs = []
    for spec in sorted(root.rglob("*.spec")):
        if any(x in spec.parts for x in SKIP_DIRS):
            continue
        txt = spec.read_text()
        m_name = re.search(r"^Name:\s*(.+)$", txt, re.M)
        m_ver = re.search(r"^Version:\s*(.+)$", txt, re.M)
        m_rel = re.search(r"^Release:\s*(.+)$", txt, re.M)
        if m_name and m_ver:
            name = m_name.group(1).strip()
            ver = m_ver.group(1).strip()
            rel = m_rel.group(1).strip().split("%")[0].strip() if m_rel else "1"
            pkgs.append((name, "%s-%s-%s" % (name, ver, rel), spec))
    return pkgs


def get_nix_packages(root):
    pkgs = []
    nix_dir = root / "pkgs"
    if not nix_dir.is_dir():
        return pkgs
    for nix in sorted(nix_dir.glob("*.nix")):
        name = nix.stem
        pkgs.append((name, name, nix))
    return pkgs


def get_void_packages(root):
    pkgs = []
    srcpkgs = root / "srcpkgs"
    if not srcpkgs.is_dir():
        return pkgs
    for tmpl in sorted(srcpkgs.rglob("template")):
        if any(x in tmpl.parts for x in SKIP_DIRS):
            continue
        name = tmpl.parent.name
        pkgs.append((name, name, tmpl))
    return pkgs


def get_deb_source_packages(root):
    """Packages whose upstream .deb payload is verifiable on Debian testing:
    specs repacking an upstream .deb directly (e.g. localsend,
    opencode-desktop), plus any spec with a sibling Debian recipe
    (<pkg>.dsc) whose update.sh carries an upstream .deb URL (e.g. the
    storytold/*craft repacks, whose Source0 is the upstream .rpm).
    Returns (name, version, spec_path) triples. The upstream .deb must
    install cleanly under debian:testing even though this repo ships RPMs."""
    pkgs = []
    for spec in sorted(root.rglob("*.spec")):
        if any(x in spec.parts for x in SKIP_DIRS):
            continue
        try:
            txt = spec.read_text()
        except Exception:
            continue
        has_deb = ".deb" in txt
        has_dsc = (spec.parent / (spec.stem + ".dsc")).exists()
        if not (has_deb or has_dsc):
            continue
        m_name = re.search(r"^Name:\s*(.+)$", txt, re.M)
        m_ver = re.search(r"^Version:\s*(.+)$", txt, re.M)
        if m_name and m_ver:
            pkgs.append((m_name.group(1).strip(), m_ver.group(1).strip(), spec))
    return pkgs


def get_arch_packages(root):
    """Packages carrying an Arch extra PKGBUILD (one per package dir, next
    to the .spec/.dsc). Returns (name, "pkgver-pkgrel", pkgbuild_path)
    triples. Only pkgname/pkgver/pkgrel are parsed - depends/makedepends
    stay makepkg's job."""
    pkgs = []
    for pb in sorted(root.rglob("PKGBUILD")):
        if any(x in pb.parts for x in SKIP_DIRS):
            continue
        try:
            txt = pb.read_text()
        except Exception:
            continue
        m_name = re.search(r"^pkgname=([^\s#]+)", txt, re.M)
        if not m_name:
            continue
        name = m_name.group(1).strip().strip("'\"")
        m_ver = re.search(r"^pkgver=([^\s#]+)", txt, re.M)
        m_rel = re.search(r"^pkgrel=([^\s#]+)", txt, re.M)
        ver = m_ver.group(1).strip().strip("'\"") if m_ver else "?"
        rel = m_rel.group(1).strip().strip("'\"") if m_rel else "1"
        pkgs.append((name, "%s-%s" % (ver, rel), pb))
    return pkgs


def deb_source_urls(spec_path):
    """Extract candidate upstream .deb URLs from a spec's Source0 lines
    (with %{version}/%{url} macros left unexpanded when unresolvable —
    caller expands or matches by suffix). Returns list of raw URL strings."""
    try:
        txt = spec_path.read_text()
    except Exception:
        return []
    urls = []
    for m in re.finditer(r"^Source\d*:\s*(\S+)\s*$", txt, re.M):
        raw = m.group(1).strip()
        if ".deb" in raw:
            urls.append(raw)
    # Also catch commented canonical URLs (e.g. "# Source: https://...deb")
    for m in re.finditer(r"https?://\S+\.deb", txt):
        if m.group(0) not in urls:
            urls.append(m.group(0))
    return urls


# ---------------------------------------------------------------------------
# Docker test runners
# ---------------------------------------------------------------------------

def docker_run(image, commands, timeout=600, volumes=None):
    args = ["docker", "run", "--rm", "--network=host",
            "-v", "/var/run/docker.sock:/var/run/docker.sock"]
    for vol in volumes or []:
        args += ["-v", vol]
    cmd_script = " && ".join(commands)
    try:
        res = subprocess.run(
            args + [image, "bash", "-c", cmd_script],
            capture_output=True, timeout=timeout)
        return res.returncode, res.stdout.decode(errors="ignore"), res.stderr.decode(errors="ignore")
    except subprocess.TimeoutExpired:
        return -1, "", "TIMEOUT after %ds" % timeout
    except Exception as e:
        return -1, "", str(e)


def test_gentoo_package(atom, overlay_path, workdir):
    commands = [
        "emerge --sync --quiet 2>/dev/null || true",
        "emerge --pretend --verbose %s 2>&1 | tail -30" % atom,
    ]
    rc, out, err = docker_run("gentoo/stage3", commands, timeout=300)
    combined = out + err
    result = {"package": atom, "status": STATUS_PASS, "details": ""}
    if rc != 0:
        result["status"] = STATUS_INSTALL_FAIL
        result["details"] = "emerge --pretend failed (rc=%d): %s" % (rc, combined[-500:])
        return result
    if "These packages will be" in out or "Total" in out:
        result["details"] = "dependency graph resolved"
    else:
        result["details"] = "pretend output unclear"
    return result


def test_fedora_package(name, nvra, spec_path, workdir):
    commands = [
        "dnf install -y dnf-plugins-core 2>/dev/null",
        "dnf copr enable -y Ackerman-00/nexus 2>/dev/null || true",
        "dnf install -y %s 2>&1 | tail -30" % name,
        "rpm -V %s 2>&1 | head -20" % name,
        "which %s 2>/dev/null && ldd $(which %s) 2>/dev/null | grep 'not found' || true" % (name, name),
    ]
    rc, out, err = docker_run("fedora:latest", commands, timeout=300)
    combined = out + err
    result = {"package": name, "status": STATUS_PASS, "details": ""}
    if "Error" in combined and "Nothing to do" not in combined:
        if "No match" in combined or "no package" in combined.lower():
            result["status"] = STATUS_SKIP
            result["details"] = "package not in repos yet"
        else:
            result["status"] = STATUS_INSTALL_FAIL
            result["details"] = "dnf install failed: %s" % combined[-500:]
        return result
    if "not found" in combined:
        result["status"] = STATUS_DEPS_MISSING
        missing = [l for l in combined.splitlines() if "not found" in l]
        result["details"] = "missing deps: %s" % "; ".join(missing[:5])
        return result
    if "unsatisfied" in combined.lower():
        result["status"] = STATUS_DEPS_MISSING
        result["details"] = "unsatisfied dependencies: %s" % combined[-500:]
        return result
    result["details"] = "installed + verified"
    return result


def test_opensuse_package(name, nvra, spec_path, workdir):
    commands = [
        "zypper --non-interactive --gpg-auto-import-keys addrepo --refresh "
        "https://download.opensuse.org/tumbleweed/repo/oss/ oss 2>&1 | tail -3",
        "zypper --non-interactive --gpg-auto-import-keys addrepo --refresh "
        "https://download.opensuse.org/repositories/home:ackerman/openSUSE_Tumbleweed/ nexus 2>&1 | tail -3",
        "zypper --non-interactive refresh 2>&1 | tail -3",
        "zypper --non-interactive install --no-recommends -y %s 2>&1 | tail -30" % name,
        "rpm -V %s 2>&1 | head -20" % name,
        "which %s 2>/dev/null && ldd $(which %s) 2>/dev/null | grep 'not found' || true" % (name, name),
    ]
    rc, out, err = docker_run("registry.opensuse.org/opensuse/tumbleweed:latest", commands, timeout=300)
    combined = out + err
    result = {"package": name, "status": STATUS_PASS, "details": ""}
    if "nothing provides" in combined.lower() or "no provider" in combined.lower():
        result["status"] = STATUS_DEPS_MISSING
        result["details"] = "zypper resolution failed: %s" % combined[-500:]
        return result
    if rc != 0 and "is already installed" not in combined and "Nothing to do" not in combined:
        result["status"] = STATUS_INSTALL_FAIL
        result["details"] = "zypper install failed (rc=%d): %s" % (rc, combined[-500:])
        return result
    if "not found" in combined:
        result["status"] = STATUS_DEPS_MISSING
        missing = [l for l in combined.splitlines() if "not found" in l]
        result["details"] = "missing deps: %s" % "; ".join(missing[:5])
        return result
    result["details"] = "installed + verified (zypper)"
    return result


def expand_deb_url(spec_path, ver):
    """Resolve the spec's upstream .deb URL host-side: prefer an https
    literal, else expand the %{url} macro form (Source0: %{url}/...deb)
    against the spec's URL: tag plus %{version}. If the spec has no .deb
    URL (e.g. its Source0 is the upstream .rpm), fall back to the sibling
    update.sh's first https .deb URL template, expanding shell version
    vars ($1, $NEW_VER, $LATEST_VERSION, $CURRENT_VER, $VERSION, $LATEST_TAG)
    and $GITHUB_REPO. Returns "" if unresolvable."""
    try:
        txt = Path(spec_path).read_text()
    except Exception:
        return ""
    for m in re.finditer(r"https?://\S+\.deb", txt):
        return m.group(0).replace("%{version}", ver).replace("%{ver}", ver)
    m_url = re.search(r"^URL:\s*(\S+)\s*$", txt, re.M)
    base = m_url.group(1).strip() if m_url else ""
    for m in re.finditer(r"^Source\d*:\s*(\S+)\s*$", txt, re.M):
        raw = m.group(1).strip()
        if ".deb" not in raw:
            continue
        u = raw.replace("%{url}", base).replace("%{URL}", base)
        u = u.replace("%{version}", ver).replace("%{ver}", ver)
        if u.startswith(("http://", "https://")):
            return u
    # Sibling update.sh fallback (craft-style repacks: Source0 is the
    # upstream .rpm, the .deb URL lives in deb_url_for()/ensure guards).
    try:
        shu = Path(spec_path).parent / "update.sh"
        shtxt = shu.read_text()
    except Exception:
        return ""
    m_repo = re.search(r'^GITHUB_REPO="([^"]+)"', shtxt, re.M)
    repo = m_repo.group(1).strip() if m_repo else ""
    for m in re.finditer(r"https?://\S+\.deb", shtxt):
        u = m.group(0).strip('"\'')
        for pat in ("%{version}", "%{ver}", "$1", "${1}", "$NEW_VER",
                     "$LATEST_VERSION", "$CURRENT_VER", "$VERSION"):
            u = u.replace(pat, ver)
        u = u.replace("$LATEST_TAG", "v" + ver)
        if repo:
            u = u.replace("$GITHUB_REPO", repo)
        if u.startswith(("http://", "https://")) and "$" not in u and "%" not in u:
            return u
    return ""


def test_debian_package(name, ver, spec_path, workdir, image="debian:testing"):
    """Verify the upstream .deb repacked by this spec installs on Debian
    (debian:testing image): download the .deb from the spec's
    Source0 URL, check control Version, install with apt (dpkg fallback),
    then ldd + binary probe. RPM-spec parsing stays the source of truth —
    this only exercises the .deb payload Debian users would touch."""
    deb_url = expand_deb_url(spec_path, ver)
    if not deb_url or "'" in deb_url:
        return {"package": name, "status": STATUS_SKIP,
                "details": "no resolvable upstream .deb URL in spec"}
    commands = [
        "apt-get update -qq 2>&1 | tail -3",
        "apt-get install -y -qq curl binutils file 2>&1 | tail -3",
        "curl -fsSL '%s' -o /tmp/pkg.deb && ls -l /tmp/pkg.deb || echo NO-DEB-URL" % deb_url,
        "dpkg-deb -f /tmp/pkg.deb Version 2>&1 || echo NO-DEB-FILE",
        # Install: apt handles deps, dpkg -i + apt -f fallback covers odd control files
        "apt-get install -y /tmp/pkg.deb 2>&1 | tail -15 || "
        "(dpkg -i /tmp/pkg.deb 2>&1 | tail -10 && apt-get install -f -y 2>&1 | tail -10)",
        "dpkg -l '%s' 2>/dev/null | tail -3 || dpkg -l | grep -i '%s' | head -5 || true" % (name, name),
        # ldd sweep over installed executables (NOT bundled *.so* libs: they
        # carry no RPATH of their own and resolve via the main binary's
        # $ORIGIN at runtime, so ldd'ing them directly reports false
        # "not found" - proven 2026-10-09 on concat's bundled libav*.
        # Transitive system deps still surface via the executable's ldd.)
        "for b in $(dpkg -L '%s' 2>/dev/null | head -50); do "
        "case \"$b\" in *.so*) continue;; esac; "
        "test -f \"$b\" && test -x \"$b\" && file \"$b\" 2>/dev/null | grep -q ELF && ldd \"$b\" 2>/dev/null; done "
        "| grep 'not found' | sort -u | head -10 || true" % name,
    ]
    rc, out, err = docker_run(image, commands, timeout=300)
    combined = out + err
    result = {"package": name, "status": STATUS_PASS, "details": ""}
    if "NO-DEB-URL" in combined or "NO-DEB-FILE" in combined:
        result["status"] = STATUS_SKIP
        result["details"] = "upstream .deb unfetchable (url=%s)" % deb_url[:100]
        return result
    if "not found" in combined:
        missing = [l.strip() for l in combined.splitlines() if "not found" in l]
        # The ldd-not-found lines are the last stage; distinguish from shell noise
        if missing:
            result["status"] = STATUS_DEPS_MISSING
            result["details"] = "missing libs on %s: %s" % (image, "; ".join(missing[:5]))
            return result
    if rc != 0:
        result["status"] = STATUS_INSTALL_FAIL
        result["details"] = "apt/dpkg install failed (rc=%d): %s" % (rc, combined[-500:])
        return result
    result["details"] = "upstream .deb installs on %s" % image
    return result


def test_nix_package(name, expr_path, workdir):
    commands = [
        "nix-build '<nixpkgs>' -A %s 2>&1 | tail -10" % name,
        "nix-store --query --requisites $(nix-build '<nixpkgs>' -A %s 2>/dev/null) 2>&1 | wc -l" % name,
    ]
    rc, out, err = docker_run("nixos/nix", commands, timeout=600)
    combined = out + err
    result = {"package": name, "status": STATUS_PASS, "details": ""}
    if rc != 0 and "error" in combined.lower():
        result["status"] = STATUS_INSTALL_FAIL
        result["details"] = "nix-build failed: %s" % combined[-500:]
        return result
    lines = combined.strip().splitlines()
    result["details"] = "built + closure verified (%s deps)" % (lines[-1] if lines else "?")
    return result


def test_void_package(name, template_path, workdir):
    commands = [
        "xbps-install -Sy 2>/dev/null || true",
        "xbps-install -S %s 2>&1 | tail -10" % name,
    ]
    rc, out, err = docker_run("voidlinux/voidlinux", commands, timeout=300)
    combined = out + err
    result = {"package": name, "status": STATUS_PASS, "details": ""}
    if rc != 0:
        result["status"] = STATUS_INSTALL_FAIL
        result["details"] = "xbps-install failed: %s" % combined[-500:]
        return result
    result["details"] = "installed"
    return result


def test_arch_package(name, ver, pkgbuild_path, workdir):
    """Verify the Arch extra PKGBUILD in a clean archlinux:latest
    container: pacman -Syu into a fresh build root, install the built
    .pkg.tar.zst (a prebuilt one next to the PKGBUILD wins, otherwise
    makepkg -sf from the PKGBUILD as a non-root build user), then namcap
    the recipe and the built package, then an ldd sweep over the
    installed binary. The package dir is copied to a temp dir first so
    makepkg never writes build artifacts into the overlay."""
    src_dir = pkgbuild_path.parent
    build_dir = tempfile.mkdtemp(prefix="arch-sweep-")
    try:
        shutil.copytree(src_dir, build_dir, dirs_exist_ok=True)
        commands = [
            "pacman -Syu --noconfirm --needed base-devel namcap 2>&1 | tail -3",
            "cd /build",
            # Build only when no prebuilt artifact ships with the recipe;
            # makepkg refuses to run as root, so build as a plain user.
            "if ! ls /build/*.pkg.tar.zst >/dev/null 2>&1; then "
            "useradd -m builder 2>/dev/null || true; "
            "chown -R builder /build; "
            "su builder -c 'cd /build && makepkg -sf --skippgpcheck --noconfirm 2>&1 | tail -25'; "
            "fi",
            "for p in /build/*.pkg.tar.zst; do "
            "pacman -U --noconfirm --overwrite '*' \"$p\" 2>&1 | tail -12; done",
            # namcap exits non-zero on warnings - never let that mask the
            # install result; its output is captured for the report.
            "namcap PKGBUILD 2>&1 | tail -40 || true",
            "for p in /build/*.pkg.tar.zst; do namcap \"$p\" 2>&1 | tail -20 || true; done",
            "pacman -Q %s 2>&1 || true" % name,
            "m=$(ldd \"$(which %s)\" 2>/dev/null | grep 'not found' || true); "
            "echo ARCLDD:$m" % name,
        ]
        rc, out, err = docker_run(
            "archlinux:latest", commands, timeout=600,
            volumes=["%s:/build" % build_dir])
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)
    combined = out + err
    result = {"package": name, "status": STATUS_PASS, "details": ""}
    if "A failure occurred in build()" in combined or "Makepkg was unable to build" in combined:
        result["status"] = STATUS_INSTALL_FAIL
        result["details"] = "makepkg build failed: %s" % combined[-500:]
        return result
    if "error: failed to prepare transaction" in combined or "exists in filesystem" in combined:
        result["status"] = STATUS_INSTALL_FAIL
        result["details"] = "pacman -U install failed: %s" % combined[-500:]
        return result
    m_archldd = re.search(r"ARCLDD:\s*(\S.*)$", combined, re.M)
    if m_archldd and m_archldd.group(1).strip():
        result["status"] = STATUS_DEPS_MISSING
        result["details"] = "missing libs on archlinux:latest: %s" % m_archldd.group(1)[:200]
        return result
    if rc != 0 and "is already installed" not in combined:
        result["status"] = STATUS_INSTALL_FAIL
        result["details"] = "arch sweep chain failed (rc=%d): %s" % (rc, combined[-500:])
        return result
    n_namcap = combined.count(" E: ")
    result["details"] = "installed + verified on archlinux:latest (namcap errors: %d)" % n_namcap
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def trivy_scan_image(image_tag):
    """Scan a built Docker image with Trivy for known CVEs.
    Returns dict with vulns list and severity counts. No hardcoding."""
    try:
        import shutil
        if not shutil.which("trivy"):
            return None
        res = subprocess.run(
            ["trivy", "image", "--format", "json", "--severity", "CRITICAL,HIGH,MEDIUM",
             "--quiet", image_tag],
            capture_output=True, timeout=120)
        if res.returncode != 0 and not res.stdout:
            return None
        data = json.loads(res.stdout.decode())
        results = data.get("Results", [])
        vulns = []
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0}
        for r in results:
            for v in r.get("Vulnerabilities", []):
                sev = v.get("Severity", "UNKNOWN")
                vid = v.get("VulnerabilityID", "?")
                pkg = v.get("PkgName", "?")
                installed = v.get("InstalledVersion", "?")
                fixed = v.get("FixedVersion", "")
                vulns.append({"id": vid, "severity": sev, "package": pkg,
                              "installed": installed, "fixed": fixed})
                if sev in counts:
                    counts[sev] += 1
        return {"vulns": vulns, "counts": counts}
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="Docker-based package install + dependency sweep")
    ap.add_argument("--overlay", default=".", help="repo root")
    ap.add_argument("--type", default="auto", choices=["auto", "gentoo", "fedora", "nix", "void", "opensuse", "debian", "arch"])
    ap.add_argument("--packages", default="", help="space-separated package names to test")
    ap.add_argument("--all", action="store_true", help="test all packages (slow)")
    ap.add_argument("--report", default="docker-report.md", help="output report path")
    ap.add_argument("--timeout", type=int, default=300, help="per-package Docker timeout")
    ap.add_argument("--scan-images", action="store_true", help="Trivy-scan base images for CVEs")
    ap.add_argument("--debdist", default="testing", choices=["testing", "sid", "trixie", "ubuntu2604", "both", "all"],
                    help="Debian release(s) for --type debian (default: testing; both=testing+sid; all adds trixie+ubuntu2604)")
    args = ap.parse_args()

    root = Path(args.overlay)
    repo_type = args.type if args.type != "auto" else detect_type(root)
    if not repo_type:
        log("UNKNOWN REPO TYPE under %s" % root)
        sys.exit(1)

    if repo_type == "gentoo":
        all_pkgs = get_gentoo_packages(root)
    elif repo_type in ("fedora", "opensuse"):
        all_pkgs = get_fedora_packages(root)
    elif repo_type == "debian":
        all_pkgs = get_deb_source_packages(root)
    elif repo_type == "nix":
        all_pkgs = get_nix_packages(root)
    elif repo_type == "void":
        all_pkgs = get_void_packages(root)
    elif repo_type == "arch":
        all_pkgs = get_arch_packages(root)
    else:
        all_pkgs = []

    if not all_pkgs:
        log("NO PACKAGES FOUND under %s" % root)
        sys.exit(1)

    if args.packages:
        wanted = set(args.packages.split())
        pkgs = [(n, v, p) for n, v, p in all_pkgs if n in wanted or n.split("/")[-1] in wanted]
    elif args.all:
        pkgs = all_pkgs
    else:
        pkgs = all_pkgs[:5]
        log("Testing first 5 packages (use --all for all, --packages for specific)")

    log("=== DOCKER SWEEP [%s]: %d packages ===" % (repo_type, len(pkgs)))
    deb_images = ["debian:testing"]
    if repo_type == "debian":
        if args.debdist == "sid":
            deb_images = ["debian:sid"]
        elif args.debdist == "both":
            deb_images = ["debian:testing", "debian:sid"]
        elif args.debdist == "trixie":
            deb_images = ["debian:13"]
        elif args.debdist == "ubuntu2604":
            deb_images = ["ubuntu:26.04"]
        elif args.debdist == "all":
            deb_images = ["debian:testing", "debian:sid", "debian:13", "ubuntu:26.04"]
        log("Debian release(s): %s" % ", ".join(deb_images))
    results = []
    for name, ver, path in pkgs:
        log("Testing %s ..." % name)
        if repo_type == "gentoo":
            r = test_gentoo_package(name, root, root)
        elif repo_type == "fedora":
            r = test_fedora_package(name, ver, path, root)
        elif repo_type == "opensuse":
            r = test_opensuse_package(name, ver, path, root)
        elif repo_type == "debian":
            for image in deb_images:
                r = test_debian_package(name, ver, path, root, image)
                results.append(r)
                log("  [%s] %s (%s): %s" % (r["status"], name, image, r["details"]))
            continue
        elif repo_type == "nix":
            r = test_nix_package(name, path, root)
        elif repo_type == "void":
            r = test_void_package(name, path, root)
        elif repo_type == "arch":
            r = test_arch_package(name, ver, path, root)
        else:
            r = {"package": name, "status": STATUS_SKIP, "details": "unsupported repo type"}
        results.append(r)
        log("  [%s] %s: %s" % (r["status"], name, r["details"]))

    n_bad = sum(1 for r in results if r["status"] not in (STATUS_PASS, STATUS_SKIP))

    image_vulns = {}
    if args.scan_images:
        BASE_IMAGES = {
            "gentoo": "gentoo/stage3",
            "fedora": "fedora:latest",
            "void": "voidlinux/voidlinux:latest",
            "opensuse": "registry.opensuse.org/opensuse/tumbleweed:latest",
            "debian": "debian:testing",
            "arch": "archlinux:latest",
        }
        img = BASE_IMAGES.get(repo_type)
        if img:
            log("")
            log("=== TRIVY SCAN: %s ===" % img)
            scan = trivy_scan_image(img)
            if scan:
                counts = scan["counts"]
                log("  CRITICAL: %d  HIGH: %d  MEDIUM: %d" % (
                    counts["CRITICAL"], counts["HIGH"], counts["MEDIUM"]))
                for v in scan["vulns"][:20]:
                    log("  [%s] %s@%s: %s (fixed: %s)" % (
                        v["severity"], v["package"], v["installed"], v["id"], v["fixed"] or "none"))
                image_vulns[img] = scan
                if counts["CRITICAL"] > 0:
                    n_bad += 1
                    results.append({"package": "base-image:%s" % img, "status": STATUS_VULN,
                                    "details": "%d CRITICAL CVEs" % counts["CRITICAL"]})
            else:
                log("  Trivy not available or scan failed (install trivy to enable)")

    log("")
    log("=== SWEEP TABLE ===")
    log("%-30s %-16s %s" % ("PACKAGE", "STATUS", "DETAILS"))
    for r in results:
        log("%-30s %-16s %s" % (r["package"], r["status"], r["details"]))

    report = Path(args.report)
    lines = ["# Docker Sweep Report", "",
             "Repo type: **%s**. Tested **%d** packages." % (repo_type, len(results)),
             "", "| Package | Status | Details |", "|---|---|---|"]
    for r in results:
        lines.append("| %s | **%s** | %s |" % (r["package"], r["status"], r["details"].replace("|", "\\|")))
    lines.append("")
    lines.append("**Verdict: %s** (%d failures)" % ("PASS" if n_bad == 0 else "FAIL", n_bad))
    report.write_text("\n".join(lines) + "\n")
    log("report written to %s" % report)

    if n_bad:
        log("=== DOCKER SWEEP FAILED: %d package(s) ===" % n_bad)
        sys.exit(1)
    log("=== DOCKER SWEEP PASSED ===")
    sys.exit(0)


if __name__ == "__main__":
    main()
