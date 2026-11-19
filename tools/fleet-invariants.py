#!/usr/bin/env python3
"""Fleet invariants no single package build can prove.

Each check reads the recipes as data: the defect it catches shipped once
(chrome-sandbox packaged 0755, an updater manifest surviving install), so a
clean build is not evidence of a correct package.
"""
import argparse
import glob
import os
import re
import sys
import tempfile
import textwrap

ALLOWED_EMAILS = {
    "noreply@example.com",
    "41898282+opencode-agent[bot]@users.noreply.github.com",
}
HEADING = re.compile(r"^[-A-Za-z]{3} [A-Za-z]{3} [ 0-9]\d \d\d:\d\d:\d\d [A-Z]+ \d{4} - ")
SKIP_DIRS = {".git", "__pycache__", "node_modules"}


def packages(root):
    out = []
    for spec in sorted(glob.glob(os.path.join(root, "*", "*.spec"))):
        out.append(os.path.dirname(spec))
    return out


def read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def check_exclusive_arch(root, pkgs):
    findings = []
    for p in pkgs:
        spec = os.path.join(p, os.path.basename(p) + ".spec")
        if not re.search(r"^ExclusiveArch:\s*x86_64\s*$", read(spec), re.M):
            findings.append(f"{os.path.basename(p)}: spec lacks 'ExclusiveArch: x86_64'")
    return findings


def check_updater_strip(root, pkgs):
    findings = []
    for p in pkgs:
        name = os.path.basename(p)
        spec = os.path.join(p, name + ".spec")
        if "app-update.yml" not in read(spec):
            findings.append(f"{name}: spec has no in-app updater strip (resources/app-update.yml)")
    return findings


def check_sandbox_attr(root, pkgs):
    findings = []
    for p in pkgs:
        name = os.path.basename(p)
        text = read(os.path.join(p, name + ".spec"))
        if "chrome-sandbox" in text and "%attr(4755" not in text:
            findings.append(f"{name}: ships chrome-sandbox without %attr(4755, ...)")
    return findings


def check_sandbox_fixperms(root, pkgs):
    findings = []
    for p in pkgs:
        name = os.path.basename(p)
        if "chrome-sandbox" not in read(os.path.join(p, name + ".spec")):
            continue
        rules = os.path.join(p, "debian.rules")
        if os.path.exists(rules) and "override_dh_fixperms" not in read(rules):
            findings.append(f"{name}: debian.rules has no override_dh_fixperms for the 4755 sandbox")
    return findings


def macro_version(spec_text):
    m = re.search(r"^Version:\s*(\S+)", spec_text, re.M)
    if not m:
        return None
    ver = m.group(1)
    for mac in ("base_version", "gitdate", "shortcommit"):
        g = re.search(r"^%global\s+" + mac + r"\s+(\S+)", spec_text, re.M)
        if g:
            ver = ver.replace("%{" + mac + "}", g.group(1))
    return ver


def field(text, name):
    out, grab = [], False
    for ln in text.splitlines():
        if grab:
            out.append(ln.strip())
            grab = ln.rstrip().endswith(",")
            continue
        if ln.startswith(name + ":"):
            out.append(ln.split(":", 1)[1].strip())
            grab = ln.rstrip().endswith(",")
    return " ".join(out)


def toks(value):
    return [t.strip() for t in value.split(",") if t.strip()]


def check_deb_recipes(root, pkgs):
    findings = []
    for p in pkgs:
        name = os.path.basename(p)
        spec = os.path.join(p, name + ".spec")
        dsc = os.path.join(p, name + ".dsc")
        control = os.path.join(p, "debian.control")
        text = read(spec)
        library_only = ("%{_libdir}" in text and "%{_bindir}" not in text
                        and "%{_datadir}/applications" not in text and "/opt/" not in text)
        if not os.path.exists(dsc):
            if not library_only:
                findings.append(f"{name}: no .dsc and the spec is not library-only")
            continue
        if not os.path.exists(control):
            findings.append(f"{name}: .dsc without debian.control")
            continue
        dtext, ctext = read(dsc), read(control)
        spec_ver, dsc_ver = macro_version(text), re.search(r"^Version:\s*(\S+)", dtext, re.M)
        dsc_ver = dsc_ver.group(1) if dsc_ver else None
        if spec_ver and dsc_ver and not spec_ver.startswith("%") and spec_ver != dsc_ver:
            findings.append(f"{name}: .dsc Version {dsc_ver} != spec Version {spec_ver}")
        binary = re.search(r"^Binary:\s*(\S+)", dtext, re.M)
        pkg = re.search(r"^Package:\s*(\S+)", ctext, re.M)
        if binary and pkg and binary.group(1) != pkg.group(1):
            findings.append(f"{name}: .dsc Binary {binary.group(1)} != debian.control Package {pkg.group(1)}")
        missing = [t for t in toks(field(ctext, "Build-Depends")) if t not in toks(field(dtext, "Build-Depends"))]
        if missing:
            findings.append(f"{name}: .dsc Build-Depends lacks {missing}")
        tar = re.search(r"^Debtransform-Tar:\s*(\S+)", dtext, re.M)
        if not tar:
            findings.append(f"{name}: .dsc has no Debtransform-Tar")
        elif dsc_ver and not tar_names_version(dsc_ver, tar.group(1), text):
            findings.append(f"{name}: Debtransform-Tar {tar.group(1)} does not carry version {dsc_ver}")
        head = re.search(r"^\S+ \(([^)]+)\) ", read(os.path.join(p, "debian.changelog")) if
                         os.path.exists(os.path.join(p, "debian.changelog")) else "", re.M)
        if dsc_ver and head and not head.group(1).startswith(dsc_ver):
            findings.append(f"{name}: debian.changelog head {head.group(1)} != .dsc Version {dsc_ver}")
    return findings


def tar_names_version(version, tar, spec_text):
    # snapshot recipes name the orig tar by shortcommit, release recipes by version
    def norm(s):
        return re.sub(r"[^0-9a-z.]", "", s.lower())
    if norm(version) in norm(tar):
        return True
    short = re.search(r"^%global\s+shortcommit\s+(\S+)", spec_text, re.M)
    if short and norm(short.group(1)) in norm(tar):
        return True
    lead = re.match(r"[0-9]+(?:\.[0-9]+)*", version)
    return bool(lead) and norm(lead.group(0)) in norm(tar)


def check_readme(root, pkgs):
    readme_path = os.path.join(root, "README.md")
    if not os.path.exists(readme_path):
        return ["README.md missing"]
    readme = read(readme_path)
    return [f"{os.path.basename(p)}: package dir absent from README.md"
            for p in pkgs if os.path.basename(p) not in readme]


def parse_probes(root):
    path = os.path.join(root, "tools", "probes.txt")
    if not os.path.exists(path):
        return None
    rows = {}
    for line in read(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [q.strip() for q in line.split("|")]
        if len(parts) < 3 or not parts[0]:
            continue
        rows[parts[0]] = (parts[1], parts[2])
    return rows


def check_probes(root, pkgs):
    # install probes name what apt/zypper actually install, so they must match the recipes
    rows = parse_probes(root)
    if rows is None:
        return ["tools/probes.txt missing"]
    findings = []
    dirs = {os.path.basename(p) for p in pkgs}
    for p in pkgs:
        name = os.path.basename(p)
        if name not in rows:
            findings.append(f"{name}: no row in tools/probes.txt")
            continue
        rpm_name, deb_name = rows[name]
        spec = read(os.path.join(p, name + ".spec"))
        declared = re.search(r"^Name:\s*(\S+)", spec, re.M)
        declared = declared.group(1) if declared else name
        sub = re.findall(r"^%package\s+-n\s+(\S+)", spec, re.M)
        if rpm_name != declared and rpm_name not in sub:
            findings.append(f"{name}: probes rpm name {rpm_name} is neither the spec Name nor a declared subpackage")
        dsc = os.path.join(p, name + ".dsc")
        if os.path.exists(dsc):
            binary = re.search(r"^Binary:\s*(\S+)", read(dsc), re.M)
            if binary and deb_name != binary.group(1):
                findings.append(f"{name}: probes deb name {deb_name} != .dsc Binary {binary.group(1)}")
    for extra in sorted(set(rows) - dirs):
        findings.append(f"{extra}: probes row has no package directory")
    return findings


def check_packager_email(root, pkgs):
    # identity carriers only: a copyright file legitimately names upstream authors
    findings = []
    addr = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    owner = re.compile(r"Ackerman-00")
    identity = re.compile(r"^(?:Maintainer:|-- |\* .* - )")
    recipe_files = {".spec", ".changes", ".dsc", ".control", ".changelog", ".rules", ".sh"}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1]
            if ext not in recipe_files:
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root)
            for line_no, line in enumerate(read(path).splitlines(), 1):
                hits = [h for h in addr.findall(line) if h not in ALLOWED_EMAILS]
                if not hits:
                    continue
                if owner.search(line) or identity.match(line.strip()):
                    findings.append(f"{rel}:{line_no}: non-placeholder address {hits[0]}")
    return findings


CHECKS = [
    ("exclusive-arch", check_exclusive_arch),
    ("updater-strip", check_updater_strip),
    ("sandbox-attr", check_sandbox_attr),
    ("sandbox-fixperms", check_sandbox_fixperms),
    ("deb-recipes", check_deb_recipes),
    ("install-probes", check_probes),
    ("readme-coverage", check_readme),
    ("packager-email", check_packager_email),
]


def run(root):
    pkgs = packages(root)
    if not pkgs:
        return 1, ["no */*.spec found under " + root]
    findings = []
    for _name, fn in CHECKS:
        findings.extend(fn(root, pkgs))
    return (1 if findings else 0), findings


def write_fixture(root, layout):
    for rel, body in layout.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(textwrap.dedent(body))


def self_test():
    good_pkg = """
    Name:           demo
    Version:        1.0
    ExclusiveArch:  x86_64
    %install
    find %{buildroot} -name resources/app-update.yml -delete
    %attr(4755, root, root) %verify(not mode) /opt/demo/chrome-sandbox
    """
    checks, failures = [], []
    seen = []

    def case(label, layout, expect_fail):
        seen.append(label)
        with tempfile.TemporaryDirectory() as tmp:
            write_fixture(tmp, layout)
            rc, findings = run(tmp)
            if (rc == 1) != expect_fail:
                failures.append(f"{label}: expected {'finding' if expect_fail else 'clean'}, got {findings}")

    dsc_ok = """
    Version: 1.0
    Binary: demo
    Build-Depends: debhelper-compat (= 13)
    Debtransform-Tar: demo-1.0.tar.gz
    """
    control_ok = """
    Package: demo
    Build-Depends: debhelper-compat (= 13)
    """
    full_ok = {
        "demo/demo.spec": good_pkg,
        "demo/demo.dsc": dsc_ok,
        "demo/debian.control": control_ok,
        "demo/debian.rules": "override_dh_fixperms:\n",
        "demo/debian.changelog": "demo (1.0-1) unstable; urgency=medium\n\n -- Ackerman-00 <noreply@example.com>  Mon, 19 Nov 2026 00:00:00 +0000\n",
        "tools/probes.txt": "demo|demo|demo|\n",
        "README.md": "demo\n",
    }
    case("clean tree", full_ok, False)

    def mutate(key, body):
        layout = dict(full_ok)
        layout[key] = body
        return layout

    case("missing ExclusiveArch", mutate("demo/demo.spec", good_pkg.replace("ExclusiveArch:  x86_64", "")), True)
    case("missing updater strip", mutate("demo/demo.spec", good_pkg.replace("app-update.yml", "nothing")), True)
    case("sandbox without attr", mutate("demo/demo.spec", good_pkg.replace("%attr(4755", "%attr(0755")), True)
    case("sandbox without fixperms", mutate("demo/debian.rules", "override_lintian:\n"), True)
    case("dsc version drift", mutate("demo/demo.dsc", dsc_ok.replace("Version: 1.0", "Version: 1.1")), True)
    case("binary drift", mutate("demo/demo.dsc", dsc_ok.replace("Binary: demo", "Binary: other")), True)
    case("build-depends gap", mutate("demo/debian.control", "Package: demo\nBuild-Depends: debhelper-compat (= 13), lintian\n"), True)
    case("tar version drift", mutate("demo/demo.dsc", dsc_ok.replace("demo-1.0.tar.gz", "demo-0.9.tar.gz")), True)
    case("changelog head drift", mutate("demo/debian.changelog", "demo (0.9-1) unstable; urgency=medium\n"), True)
    case("probes deb name drift", mutate("tools/probes.txt", "demo|demo|other|\n"), True)
    case("probes row missing", mutate("tools/probes.txt", "# no rows\n"), True)
    case("readme gap", mutate("README.md", "other\n"), True)
    case("real email", mutate("demo/debian.control", control_ok + "Maintainer: dev@real-domain.example\n"), True)
    case("placeholder email", mutate("demo/debian.control", control_ok + "Maintainer: Ackerman-00 <noreply@example.com>\n"), False)

    for label, layout, expect in (
        ("library package without dsc", {k: v for k, v in full_ok.items() if not k.startswith("demo/demo.d")}, False),
    ):
        seen.append(label)
        with tempfile.TemporaryDirectory() as tmp:
            lib_spec = good_pkg.replace("Name:           demo", "Name:           demo\n    %package devel")
            lib_spec = lib_spec.replace("    %attr(4755, root, root) %verify(not mode) /opt/demo/chrome-sandbox", "    %{_libdir}/libdemo.so")
            write_fixture(tmp, dict(layout, **{"demo/demo.spec": lib_spec}))
            rc, findings = run(tmp)
            if (rc == 1) != expect:
                failures.append(f"{label}: expected {'finding' if expect else 'clean'}, got {findings}")

    for f in failures:
        print("SELFTEST FAIL " + f)
    if failures:
        return 1
    print(f"fleet-invariants self-test: {len(CHECKS)} checks, {len(seen)} fixtures, all pass")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".", help="tree to scan (default: repo root)")
    ap.add_argument("--self-test", action="store_true", help="run the fixture suite")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    rc, findings = run(args.root)
    pkgs = packages(args.root)
    for f in findings:
        print("FINDING " + f)
    print(f"fleet-invariants: {len(pkgs)} packages, {len(CHECKS)} checks, {len(findings)} findings")
    return rc


if __name__ == "__main__":
    sys.exit(main())
