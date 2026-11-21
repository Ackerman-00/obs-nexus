#!/usr/bin/env python3
# OBS source-artifact prune: keep what the recipe references, delete superseded files
"""Report or delete OBS source artifacts no local recipe references.

The keep-set is derived from the package directory (local artifacts), the
.dsc Debtransform-Tar entry, every expanded spec SourceN and _service
filename params - the same rule update-packages.yml applies inline.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

API = "https://api.opensuse.org"
PROJECT = "home:ackerman"
ART_EXTS = ('.tar.gz', '.tar.xz', '.tar.bz2', '.tar.zst', '.tgz',
            '.appimage', '.deb', '.rpm', '.zip')
SPEC_TEXT = ('.spec', '.dsc', '.sh', '.rules', '.patch', '.rpmlintrc')


def tarlike(name):
    return name.lower().endswith(ART_EXTS)


def expand(text, macros):
    cur = text
    for _ in range(4):
        new = re.sub(r"%\{(\w+)\}", lambda m: macros.get(m.group(1), m.group(0)), cur)
        new = re.sub(r"%([A-Za-z_]\w*)", lambda m: macros.get(m.group(1), m.group(0)), new)
        if new == cur:
            break
        cur = new
    return cur


def spec_macros(text):
    mac = {}
    for m in re.finditer(r"^%(?:global|define)\s+(\w+)\s+(\S+)", text, re.M):
        mac.setdefault(m.group(1), m.group(2))
    for key, tag in (("name", "Name"), ("version", "Version")):
        m = re.search(r"^%s:\s*(\S+)" % tag, text, re.M)
        if m:
            mac.setdefault(key, m.group(1))
    return mac


def spec_sources(text):
    mac = spec_macros(text)
    out = []
    for m in re.finditer(r"^Source\d+:\s*(\S+)", text, re.M):
        base = os.path.basename(m.group(1).split("?", 1)[0])
        cur = expand(base, mac)
        if "%" not in cur and tarlike(cur):
            out.append(cur)
    return out


def keep_set(pkgdir):
    keep = set()
    for f in glob.glob(os.path.join(pkgdir, "*")):
        base = os.path.basename(f)
        if os.path.isfile(f) and tarlike(base):
            keep.add(base)
    for dsc in glob.glob(os.path.join(pkgdir, "*.dsc")):
        txt = open(dsc, encoding="utf-8", errors="replace").read()
        m = re.search(r"^Debtransform-Tar:\s*(\S+)", txt, re.M)
        if m and tarlike(m.group(1)):
            keep.add(m.group(1))
    for sp in glob.glob(os.path.join(pkgdir, "*.spec")):
        keep.update(spec_sources(open(sp, encoding="utf-8", errors="replace").read()))
    for svc in glob.glob(os.path.join(pkgdir, "_service")):
        txt = open(svc, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"<param\s+name=\"filename\">\s*([^<]+?)\s*</param>", txt):
            keep.add(m.group(1))
    return keep


def stem(name):
    n = name
    for ext in ART_EXTS:
        if n.lower().endswith(ext):
            n = n[:-len(ext)]
            break
    n = re.sub(r"[0-9a-f]{7,40}", "", n, flags=re.I)
    n = re.sub(r"\d+(?:[._+~-][0-9A-Za-z]+)*", "", n)
    return re.sub(r"[-_.+]+", "-", n).strip("-").lower()


def referenced(pkgdir, name, remote_texts):
    if any(name in t for t in local_texts(pkgdir)):
        return True
    return any(name in body for body in remote_texts.values())


# changelogs name old artifacts in history; only recipe text can reference one
CHANGELOGS = (".changes", "debian.changelog", "debian.copyright", "debian.control.in")


def strip_changelog(text, is_spec):
    if is_spec:
        cut = text.find("\n%changelog")
        if cut >= 0:
            return text[:cut]
    return text


def local_texts(pkgdir):
    out = []
    for root, _dirs, files in os.walk(pkgdir):
        for f in files:
            if f.endswith(CHANGELOGS):
                continue
            p = os.path.join(root, f)
            try:
                out.append(strip_changelog(open(p, encoding="utf-8", errors="replace").read(),
                                           f.endswith(".spec")))
            except OSError:
                continue
    return out


def verdict(pkgdir, remote, remote_texts):
    if not tarlike(remote):
        return "KEEP:not-a-source-artifact"
    keep = keep_set(pkgdir)
    if remote in keep:
        return "KEEP:referenced-by-recipe"
    if referenced(pkgdir, remote, remote_texts):
        return "KEEP:referenced-in-recipe-text"
    if not keep:
        return "KEEP:no-keep-set"
    rs = stem(remote)
    ext = next((e for e in ART_EXTS if remote.lower().endswith(e)), "")
    twins = [k for k in keep if stem(k) == rs]
    twin = next((k for k in twins if k.lower().endswith(ext)), twins[0] if twins else None)
    if rs and twin:
        return "DELETE:superseded-by-%s" % twin
    return "KEEP:unproven-not-superseded"


def obs_get(url, auth):
    req = urllib.request.Request(url, headers={"User-Agent": "opensuse-nexus/1.0"})
    if auth:
        import base64
        req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def obs_delete(url, auth):
    import base64
    req = urllib.request.Request(url, method="DELETE", headers={"User-Agent": "opensuse-nexus/1.0"})
    req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.status


def remote_files(auth, pkg):
    body = obs_get("%s/source/%s/%s" % (API, PROJECT, pkg), auth)
    return re.findall(r'<entry name="([^"]+)"', body)


def remote_texts(auth, pkg, files):
    out = {}
    for f in files:
        if f.lower().endswith(SPEC_TEXT) or f == "_service":
            body = obs_get("%s/source/%s/%s/%s" % (API, PROJECT, pkg, f), auth)
            out[f] = strip_changelog(body, f.endswith(".spec"))
    return out


def selftest():
    errors = []
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "demo")
        os.makedirs(p)
        open(os.path.join(p, "demo.spec"), "w").write(
            "%global version 1.2\nName: demo\nVersion: %{version}\n"
            "Source0: https://example.invalid/demo-%{version}.tar.gz\n")
        open(os.path.join(p, "demo.dsc"), "w").write("Debtransform-Tar: demo-1.2.tar.gz\n")
        open(os.path.join(p, "demo-1.2.tar.gz"), "w").write("x")
        cases = [
            ("demo-1.2.tar.gz", "KEEP:referenced-by-recipe"),
            ("demo-1.1.tar.gz", "DELETE:superseded-by-demo-1.2.tar.gz"),
            ("demo-fix.patch", "KEEP:not-a-source-artifact"),
            ("unrelated.tar.xz", "KEEP:unproven-not-superseded"),
        ]
        for name, want in cases:
            got = verdict(p, name, {})
            if got != want:
                errors.append("%s -> %s (want %s)" % (name, got, want))
        cases_n = len(cases) + 5
        bare = os.path.join(td, "bare")
        os.makedirs(bare)
        open(os.path.join(bare, "bare.spec"), "w").write("Name: bare\n")
        got = verdict(bare, "bare-0.1.tar.gz", {})
        if got != "KEEP:no-keep-set":
            errors.append("bare -> %s (want KEEP:no-keep-set)" % got)
        # referenced only in remote recipe text must be kept
        got = verdict(p, "demo-extra.tar.gz", {"demo.dsc": "Debtransform-Extra: demo-extra.tar.gz"})
        if got != "KEEP:referenced-in-recipe-text":
            errors.append("remote-text -> %s" % got)
        # changelog history naming an old artifact must NOT keep it
        open(os.path.join(p, "demo.changes"), "w").write(
            "- version 1.1\n- repacked demo-1.1.tar.gz\n")
        got = verdict(p, "demo-1.1.tar.gz", {})
        if got != "DELETE:superseded-by-demo-1.2.tar.gz":
            errors.append("changelog-trap -> %s" % got)
        # staging filename named by update.sh is a real reference
        open(os.path.join(p, "update.sh"), "w").write("cp up.deb staging.deb\n")
        got = verdict(p, "staging.deb", {})
        if got != "KEEP:referenced-in-recipe-text":
            errors.append("update.sh-ref -> %s" % got)
        # a spec %changelog mention must not keep an old artifact either
        open(os.path.join(p, "old.spec"), "w").write(
            "Name: old\nSource0: old-1.1.tar.gz\n%changelog\n* Mon Jan 1 2026 x\n"
            "- repacked old-1.0.tar.gz\n")
        got = verdict(p, "old-1.0.tar.gz", {})
        if got != "DELETE:superseded-by-old-1.1.tar.gz":
            errors.append("spec-changelog-trap -> %s" % got)
    if errors:
        for e in errors:
            print("SELFTEST FAIL: " + e)
        return 1
    print("artifact-prune: self-test %d/%d PASS" % (cases_n, cases_n))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--package", action="append", default=[])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return selftest()
    user, pw = os.environ.get("OBS_USER", ""), os.environ.get("OBS_PASS", "")
    if not user or not pw:
        print("artifact-prune: UNVERIFIED OBS_USER/OBS_PASS absent", file=sys.stderr)
        return 2
    auth = "%s:%s" % (user, pw)
    pkgs = args.package or sorted(
        os.path.basename(os.path.dirname(sp)) for sp in glob.glob(os.path.join(args.root, "*", "*.spec")))
    report, deletes, errors = [], 0, 0
    for pkg in pkgs:
        pkgdir = os.path.join(args.root, pkg)
        try:
            files = remote_files(auth, pkg)
        except urllib.error.HTTPError as e:
            report.append({"package": pkg, "file": "-", "verdict": "UNVERIFIED:http-%s" % e.code})
            errors += 1
            continue
        texts = remote_texts(auth, pkg, files)
        for f in files:
            v = verdict(pkgdir, f, texts)
            report.append({"package": pkg, "file": f, "verdict": v})
            if v.startswith("DELETE:"):
                if args.apply:
                    try:
                        code = obs_delete("%s/source/%s/%s/%s" % (API, PROJECT, pkg, f), auth)
                        report[-1]["deleted"] = code == 200
                    except urllib.error.HTTPError as e:
                        report[-1]["deleted"] = False
                        report[-1]["verdict"] += " DELETE_FAILED_http-%s" % e.code
                        errors += 1
                        continue
                deletes += 1
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for r in report:
            print("%(package)s | %(file)s | %(verdict)s" % r + (" | deleted" if r.get("deleted") else ""))
    n = len({r["package"] for r in report})
    print("artifact-prune: %d packages, %d delete candidate(s), %d unverified%s"
          % (n, deletes, errors, " - applied" if args.apply else " - dry-run"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
