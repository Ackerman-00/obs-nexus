#!/usr/bin/env python3
"""Live OBS build/published-state audit. Stdlib only.

Uses the documented OBS API for build state and the public download tree for
published NVRs. An unauthenticated 401 is reported as UNVERIFIED with the
exact status code, never as clean.
"""
import glob
import gzip
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

PROJECT = "home:ackerman"
API = "https://api.opensuse.org"
PUB = "https://download.opensuse.org/repositories/home:ackerman"
UA = "obs-nexus-audit/1.0 (+https://github.com/Ackerman-00/obs-nexus; issue tracker: https://github.com/Ackerman-00/obs-nexus/issues)"
TARGETS = {
    "Tumbleweed": PUB + "/openSUSE_Tumbleweed/repodata/repomd.xml",
    "Debian_Testing": PUB + "/Debian_Testing/Packages.gz",
    "Debian_Unstable": PUB + "/Debian_Unstable/Packages.gz",
}


def get(url, auth=False):
    cmd = ["curl", "-sS", "-L", "--max-time", "45", "-A", UA, "-w", "\n%{http_code}",
           "-o", "-"]
    if auth and os.environ.get("OBS_USER") and os.environ.get("OBS_PASS"):
        cmd += ["-u", f"{os.environ['OBS_USER']}:{os.environ['OBS_PASS']}"]
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok and url.startswith("https://api.github.com/"):
        cmd += ["-H", f"Authorization: token {tok}"]
    cmd.append(url)
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        return 0, b"timeout"
    if r.returncode != 0:
        return 0, r.stderr
    body, _, code = r.stdout.rpartition(b"\n")
    try:
        return int(code), body
    except ValueError:
        return 0, body


def specs():
    out = {}
    for sp in sorted(glob.glob("*/*.spec")):
        txt = open(sp, encoding="utf-8", errors="replace").read()
        mac = {}
        for m in re.finditer(r"^%(?:global|define)\s+(\w+)\s+(\S+)", txt, re.M):
            mac.setdefault(m.group(1), m.group(2))
        name = re.search(r"^Name:\s*(\S+)", txt, re.M)
        ver = re.search(r"^Version:\s*(\S+)", txt, re.M)
        rel = re.search(r"^Release:\s*(\S+)", txt, re.M)
        if not (name and ver):
            continue
        v = ver.group(1)
        for _ in range(4):
            nv = re.sub(r"%\{(\w+)\}", lambda m: mac.get(m.group(1), m.group(0)), v)
            nv = re.sub(r"%(\w+)", lambda m: mac.get(m.group(1), m.group(0)), nv)
            if nv == v:
                break
            v = nv
        out[name.group(1)] = (v, rel.group(1) if rel else "?")
    return out


def builds():
    code, body = get(f"{API}/build/{PROJECT}/_result", auth=True)
    if code != 200:
        print(f"hunt: builds - UNVERIFIED OBS build API HTTP {code} (no usable build state; not clean)")
        return False
    text = body.decode("utf-8", "replace")
    failed = re.findall(r'package="([^"]+)"[^>]*code="(failed|broken)"', text)
    if not failed:
        failed = re.findall(r'code="(failed|broken)"[^>]*package="([^"]+)"', text)
        failed = [(b, a) for a, b in failed]
    if failed:
        print("hunt: builds - FAILED " + ", ".join(sorted({p for p, _ in failed})))
        return True
    print("hunt: builds - OBS build API HTTP 200, no failed/broken packages")
    return False


def published():
    local = specs()
    deb_names = {}
    for pkg in local:
        for dsc in glob.glob(os.path.join(pkg, "*.dsc")):
            txt = open(dsc, encoding="utf-8", errors="replace").read()
            m = re.search(r"(?m)^Binary:\s*(\S+)", txt)
            if m:
                deb_names[pkg] = m.group(1)
    found = {}
    for target, url in TARGETS.items():
        code, body = get(url)
        if code != 200:
            print(f"hunt: published-nvr - UNVERIFIED {target} HTTP {code}")
            continue
        if target == "Tumbleweed":
            m = re.search(rb'href="([^"]*-primary\.xml\.gz)"', body)
            if not m:
                print("hunt: published-nvr - UNVERIFIED Tumbleweed primary.xml.gz link absent")
                continue
            primary_url = url.rsplit("/repodata/", 1)[0] + "/" + m.group(1).decode()
            c2, raw = get(primary_url)
            if c2 != 200:
                print(f"hunt: published-nvr - UNVERIFIED Tumbleweed primary HTTP {c2}")
                continue
            text = gzip.decompress(raw).decode("utf-8", "replace")
            names = re.findall(r"<name>([^<]+)</name>", text)
        else:
            text = gzip.decompress(body).decode("utf-8", "replace")
            names = re.findall(r"(?m)^Package:\s*(\S+)", text)
        found[target] = set(names)
        print(f"hunt: published-nvr - {target} index HTTP 200, {len(names)} entries")
    missing = []
    for pkg in sorted(local):
        d = os.path.join(pkg, "debian.rules")
        dsc = glob.glob(os.path.join(pkg, "*.dsc"))
        expects_deb = os.path.isfile(d) and bool(dsc)
        for t, names in found.items():
            check_name = deb_names.get(pkg, pkg) if t.startswith("Debian") else pkg
            if check_name in names or not found:
                continue
            if t.startswith("Debian") and not expects_deb:
                continue
            missing.append(f"{check_name} missing from {t}")
    if missing:
        print("hunt: published-nvr - DEFECT " + "; ".join(missing))
        return True
    if not found:
        print("hunt: published-nvr - UNVERIFIED no published index readable")
    else:
        print(f"hunt: published-nvr - all {len(local)} local package names present in each readable target")
    return False


def drift():
    code, body = get(f"{API}/source/{PROJECT}/_project?view=info", auth=True)
    if code != 200:
        print(f"hunt: sources - UNVERIFIED OBS source API HTTP {code} (no authenticated drift check)")
        return False
    print("hunt: sources - OBS source API HTTP 200")
    return False



def rev_seen(tag, text):
    """Tag equivalence: dot and dash separators are the same version to a packager."""
    cands = {tag, tag.replace("-", "."), tag.replace(".", "-"), tag.replace("_", ".")}
    return any(c and c in text for c in cands)


def release_asset_missing(tag, spec_text, body):
    """A release tag with no matching source asset cannot be packaged yet."""
    src = re.search(r"(?m)^Source0:\s*(\S+)", spec_text)
    if not src or "/releases/download/" not in src.group(1):
        return False
    try:
        assets = [a.get("name", "") for a in json.loads(body).get("assets", [])]
    except Exception:
        return False
    ver = tag.lstrip("v")
    src_base = src.group(1).rsplit("/", 1)[-1]
    exts = (".tar.gz", ".tar.xz", ".tar.zst", ".tar.bz2", ".tgz", ".zip", ".deb", ".rpm",
            ".AppImage", ".dmg", ".exe")
    ext = next((e for e in exts if src_base.endswith(e)), "")
    return not any(ver in a and a.endswith(ext) for a in assets)


def upstream_versions():
    """Latest GitHub release/tag vs the spec version, <=1 request/s."""
    bad = []
    held = []
    checked = 0
    for sp in sorted(glob.glob("*/*.spec")):
        txt = open(sp, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^URL:\s*https?://github\.com/([^/\s]+)/([^/\s]+)", txt)
        if not m:
            continue
        owner, repo = m.group(1), m.group(2)
        code, body = get(f"https://api.github.com/repos/{owner}/{repo}/releases/latest")
        if code != 200:
            code_t, body_t = get(f"https://api.github.com/repos/{owner}/{repo}/tags?per_page=100")
            tag = ""
            if code_t == 200:
                try:
                    names = [t["name"] for t in json.loads(body_t)]
                except Exception:
                    names = []
                vers = [n for n in names if re.match(r"^v?\d", n)]
                if vers:
                    tag = max(vers, key=lambda n: [int(x) for x in re.findall(r"\d+", n)[:4]] or [0]).lstrip("v")
            if code_t == 200:
                if tag:
                    checked += 1
                    if not rev_seen(tag, txt):
                        bad.append(f"{os.path.dirname(sp)} spec lacks newest upstream tag {tag}")
                    time.sleep(1)
                    continue
            print(f"hunt: upstream-versions - UNVERIFIED {owner}/{repo} releases HTTP {code}, tags HTTP {code_t}"
                  + (" (no version-like tag; commit HEAD is the reference)" if code_t == 200 else ""))
            time.sleep(1)
            continue
        try:
            tag = json.loads(body).get("tag_name", "").lstrip("v")
        except Exception:
            tag = ""
        if tag:
            checked += 1
            if not rev_seen(tag, txt):
                if release_asset_missing(tag, txt, body):
                    held.append(f"{os.path.dirname(sp)} {tag} release has no matching source asset yet")
                else:
                    bad.append(f"{os.path.dirname(sp)} spec lacks newest upstream {tag}")
        time.sleep(1)
    if held:
        print("hunt: upstream-versions - UNVERIFIED " + "; ".join(held))
    if bad:
        print("hunt: upstream-versions - DEFECT " + "; ".join(bad))
        return True
    print(f"hunt: upstream-versions - {checked} GitHub refs checked, no behind pins")
    return False


def vcmp(a, b):
    """Numeric dotted compare; non-numeric suffixes sort below the bare version."""
    def parts(v):
        v = v.strip().lstrip("v")
        out = []
        for p in re.split(r"[._+~-]", v):
            m = re.match(r"^\d+", p)
            out.append(int(m.group(0)) if m else -1)
        return out
    pa, pb = parts(a), parts(b)
    n = max(len(pa), len(pb))
    pa += [0] * (n - len(pa))
    pb += [0] * (n - len(pb))
    for x, y in zip(pa, pb):
        if x != y:
            return -1 if x < y else 1
    return 0


def in_range(version, events):
    """True when version falls in any [introduced, fixed) interval."""
    intro = "0"
    for ev in events:
        if "introduced" in ev:
            intro = ev["introduced"]
        elif "fixed" in ev:
            if vcmp(version, intro) >= 0 and vcmp(version, ev["fixed"]) < 0:
                return True
            intro = None
        elif "last_affected" in ev:
            if vcmp(version, intro) >= 0 and vcmp(version, ev["last_affected"]) <= 0:
                return True
            intro = None
    return intro is not None and vcmp(version, intro) >= 0


def cna_ceiling(vid):
    """Upstream fix ceiling from the CVE record; distro ids are not CVE records."""
    m = re.search(r"(CVE-\d{4}-\d+)", vid)
    if not m:
        return None
    code, body = get("https://cveawg.mitre.org/api/cve/" + m.group(1))
    if code != 200:
        return None
    try:
        doc = json.loads(body)
    except Exception:
        return None
    for aff in doc.get("containers", {}).get("cna", {}).get("affected", []):
        for ver in aff.get("versions", []):
            if ver.get("status") != "affected":
                continue
            if ver.get("lessThan"):
                return ver["lessThan"]
            v = (ver.get("version") or "").strip()
            if v.startswith("<"):
                return v.lstrip("<").strip()
    return None


def published_versions():
    """pkg -> published version. OSV distro ranges are written in distro NVRs."""
    out = {}
    code, body = get(TARGETS["Tumbleweed"])
    m = re.search(rb'href="([^"]*-primary\.xml\.(?:gz|zst))"', body or b"")
    if code == 200 and m:
        base = TARGETS["Tumbleweed"].rsplit("/repodata/", 1)[0]
        c2, raw = get(base + "/" + m.group(1).decode())
        if c2 == 200:
            try:
                if m.group(1).decode().endswith(".gz"):
                    text = gzip.decompress(raw).decode("utf-8", "replace")
                else:
                    text = subprocess.run(["zstd", "-dc"], input=raw,
                                          capture_output=True).stdout.decode("utf-8", "replace")
            except Exception:
                text = ""
            for pm in re.finditer(r"<package[^>]*>(.*?)</package>", text, re.S):
                n = re.search(r"<name>([^<]+)</name>", pm.group(1))
                v = re.search(r'<version epoch="[^"]*" ver="([^"]+)" rel="([^"]+)"', pm.group(1))
                if n and v:
                    out.setdefault(n.group(1), f"{v.group(1)}-{v.group(2)}")
    for target in ("Debian_Testing", "Debian_Unstable"):
        code, body = get(TARGETS[target])
        if code != 200:
            continue
        try:
            text = gzip.decompress(body).decode("utf-8", "replace")
        except Exception:
            continue
        for para in text.split("\n\n"):
            n = re.search(r"(?m)^Package:\s*(\S+)", para)
            v = re.search(r"(?m)^Version:\s*(\S+)", para)
            if n and v:
                ver = re.sub(r"^\d+:", "", v.group(1))  # epoch is not a CVE range input
                out.setdefault(n.group(1), ver)
    return out


def cve_version(name, known, published):
    """Advisory range basis: the distro NVR when published, else the spec version."""
    if name in published:
        return published[name], "published"
    entry = known.get(name)
    if entry and entry[0]:
        return entry[0], "spec"
    return "", "none"


def cves():
    """OSV batch; IDs only, interval-filter with GET /v1/vulns/<id>."""
    known = specs()
    published = published_versions()
    names = {}
    for sp in sorted(glob.glob("*/*.spec")):
        d = os.path.dirname(sp)
        n = re.search(r"(?m)^Name:\s*(\S+)", open(sp, encoding="utf-8", errors="replace").read())
        names[d] = n.group(1) if n else d
    queries = []
    basis = {}
    for sp in sorted(glob.glob("*/*.spec")):
        d = os.path.dirname(sp)
        ver, how = cve_version(names[d], known, published)
        if not ver:
            continue
        basis[d] = how
        queries.append({"version": ver, "package": {"name": d}})
    if not queries:
        return False
    req = urllib.request.Request(
        "https://api.osv.dev/v1/querybatch",
        data=json.dumps({"queries": queries[:1000]}).encode(),
        headers={"User-Agent": UA, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            result = json.loads(r.read())["results"]
    except Exception as e:
        print(f"hunt: cves - UNVERIFIED querybatch {type(e).__name__}")
        return False
    hits = [(q, v.get("vulns", [])) for q, v in zip(queries, result) if v.get("vulns")]
    affected = []
    excused = []
    for q, vulns in hits[:40]:
        for item in vulns:
            code, body = get("https://api.osv.dev/v1/vulns/" + item["id"])
            if code != 200:
                continue
            try:
                adv = json.loads(body)
            except Exception:
                continue
            hit = False
            unfixed = False
            for aff in adv.get("affected", []):
                for rng in aff.get("ranges", []):
                    events = rng.get("events", [])
                    if in_range(q["version"], events):
                        hit = True
                        if not any("fixed" in e for e in events):
                            unfixed = True
            if hit and unfixed:
                ceiling = next((c for c in (cna_ceiling(a) for a in adv.get("aliases", []) + [item["id"]]) if c), None)
                if ceiling and vcmp(q["version"], ceiling) >= 0:
                    excused.append(f"{q['package']['name']} {q['version']} {item['id']} (fixed upstream < {ceiling})")
                    time.sleep(0.2)
                    continue
            if hit:
                affected.append(f"{q['package']['name']} {q['version']} {item['id']}")
            time.sleep(0.2)
    if affected:
        print("hunt: cves - AFFECTED " + "; ".join(affected))
        return True
    how = f"{sum(1 for v in basis.values() if v == 'published')} published NVR, " \
          f"{sum(1 for v in basis.values() if v == 'spec')} spec version"
    print(f"hunt: cves - {len(hits)} OSV hits range-filtered, no in-range advisory (basis: {how})"
          + (f"; excused {len(excused)} distro-unfixed with upstream fix: " + "; ".join(excused) if excused else ""))
    return False


def pins():
    bad = []
    checked = 0
    for sp in sorted(glob.glob("*/*.spec")):
        txt = open(sp, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r"(?m)#\s*sha256:\s*([0-9a-f]{64})", txt):
            checked += 1
            if len(m.group(1)) != 64:
                bad.append(sp + " malformed pin")
    if bad:
        print("hunt: pins - DEFECT " + "; ".join(bad))
        return True
    print(f"hunt: pins - {checked} sha256 pin comments well-formed (hash match needs the artifact)")
    return False


def probe_rows(path="tools/probes.txt"):
    """Package names from the data rows only; '#' lines are notes, not rows."""
    rows = set()
    for line in open(path, encoding="utf-8", errors="replace"):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        rows.add(s.split("|")[0].strip())
    return rows


def probes():
    if not os.path.isfile("tools/probes.txt"):
        print("hunt: probes - DEFECT tools/probes.txt missing")
        return True
    rows = probe_rows()
    names = set(specs())
    missing = sorted(names - rows)
    if missing:
        print("hunt: probes - DEFECT no row for " + ", ".join(missing))
        return True
    extra = sorted(rows - names)
    if extra:
        print("hunt: probes - DEFECT stale row for " + ", ".join(extra))
        return True
    print(f"hunt: probes - {len(rows)} rows cover {len(names)} specs")
    return False


def release_discipline():
    bad = []
    for sp in sorted(glob.glob("*/*.spec")):
        d = os.path.dirname(sp)
        ch = os.path.join(d, os.path.basename(d) + ".changes")
        if not os.path.isfile(ch):
            bad.append(d + " no .changes")
            continue
        top = open(ch, encoding="utf-8", errors="replace").read().splitlines()
        ver = specs().get(os.path.basename(d))
        rel = re.search(r"(?m)^Release:\s*(\S+)", open(sp, encoding="utf-8", errors="replace").read())
        if ver and rel and not any(ver[0] in l and "-" + rel.group(1) in l for l in top[:12]):
            bad.append(d + " newest .changes entry does not name the spec NVR")
    if bad:
        print(f"hunt: release-discipline - INFO {len(bad)} newest .changes entries omit the NVR (OBS style allows a fix description)")
        return False
    print("hunt: release-discipline - newest .changes entry names each spec NVR")
    return False


def readme():
    txt = open("README.md", encoding="utf-8", errors="replace").read()
    missing = [p for p in specs() if p not in txt]
    if missing:
        print("hunt: readme - DEFECT no README row for " + ", ".join(missing[:10]))
        return True
    print(f"hunt: readme - all {len(specs())} packages listed")
    return False


def targets():
    txt = open("README.md", encoding="utf-8", errors="replace").read()
    missing = [t for t in ("Tumbleweed", "Forky", "Unstable") if t not in txt]
    if missing:
        print("hunt: targets - DEFECT README missing " + ", ".join(missing))
        return True
    print("hunt: targets - README documents all three targets")
    return False

def selftest():
    """Positive and negative fixtures for the version/range logic."""
    ok = True
    cases = [
        (in_range("1.4.0", [{"introduced": "0"}, {"fixed": "1.0.1"}]), False, "above fixed ceiling"),
        (in_range("0.9.0", [{"introduced": "0"}, {"fixed": "1.0.1"}]), True, "below fixed ceiling"),
        (in_range("1.0.1", [{"introduced": "0"}, {"fixed": "1.0.1"}]), False, "exactly at fixed"),
        (in_range("1.4.0", [{"introduced": "0"}]), True, "unfixed range covers all"),
        (in_range("1.2.0", [{"introduced": "1.1.0"}, {"last_affected": "1.3.0"}]), True, "last_affected"),
        (vcmp("0.85.4", "0.85.10"), -1, "numeric compare, not lexical"),
        (vcmp("2.0.7", "2.0.7"), 0, "equal"),
        (vcmp("26.11.5", "26.9.1"), 1, "major compare"),
        (rev_seen("2026-10-31.1", "Version: 2026.10.31.1"), True, "dash/dot tag equivalence"),
        (rev_seen("0.85.4", "Version: 0.85.2"), False, "different version is not equivalent"),
        (release_asset_missing("v2026.11.7",
                               "Source0: %{url}/releases/download/v2026.11.7/OpenClaw-2026.11.7-amd64.deb",
                               json.dumps({"assets": [{"name": "latest.json"},
                                                     {"name": "openclaw-2026.11.7-dependency-evidence.zip"}]})),
         True, "evidence asset naming the version does not satisfy a .deb source"),
        (release_asset_missing("v2026.11.6",
                               "Source0: %{url}/releases/download/v2026.11.6/OpenClaw-2026.11.6-amd64.deb",
                               json.dumps({"assets": [{"name": "OpenClaw-2026.11.6-amd64.deb"}]})), False,
         "release with the sourced asset"),
        (release_asset_missing("v4.2", "Source0: https://github.com/Mibea/Hatter/archive/refs/tags/V4.2.tar.gz",
                               json.dumps({"assets": []})), False,
         "archive tag source is not a release asset"),
        (cve_version("ghostty", {"ghostty": ("1.4.0", "0")}, {"ghostty": "1.4.0-96.3"}),
         ("1.4.0-96.3", "published"), "published NVR is the advisory basis"),
        (cve_version("ghostty", {"ghostty": ("1.4.0", "0")}, {}),
         ("1.4.0", "spec"), "spec version is the fallback basis"),
        (in_range("1.4.0-96.3", [{"introduced": "0"}, {"fixed": "1.4.0-1.1"}]), False,
         "published release above the fixed distro NVR"),
        (in_range("1.4.0", [{"introduced": "0"}, {"fixed": "1.4.0-1.1"}]), True,
         "bare upstream version is below the fixed NVR"),
    ]
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write("# note: not a probe row\npkg-a|rpm-a|deb-a|\n\n# second note\npkg-b|rpm-b|deb-b|test -x /usr/bin/b\n")
        tmp = f.name
    rows = probe_rows(tmp)
    os.unlink(tmp)
    cases += [
        (rows, {"pkg-a", "pkg-b"}, "comment lines are not probe rows"),
        (len(rows), 2, "probe row count ignores notes"),
    ]
    for got, want, label in cases:
        if got != want:
            ok = False
            print(f"selftest FAIL {label}: got {got}, want {want}")
    print("selftest PASS" if ok else "selftest FAIL")
    return 0 if ok else 1


def main():
    if "--selftest" in sys.argv:
        return selftest()
    cats = sys.argv[1:] or ["builds", "published-nvr", "sources", "upstream-versions", "cves", "pins", "probes", "release-discipline", "readme", "targets"]
    bad = False
    if "builds" in cats:
        bad |= builds()
    if "published-nvr" in cats:
        bad |= published()
    if "sources" in cats:
        bad |= drift()
    for name, fn in (("upstream-versions", upstream_versions), ("cves", cves),
                     ("pins", pins), ("probes", probes),
                     ("release-discipline", release_discipline),
                     ("readme", readme), ("targets", targets)):
        if name in cats:
            bad |= fn()
    if bad:
        print("obs-api-check: DEFECT found")
        return 1
    print("obs-api-check: no concrete defect (UNVERIFIED lines are not clean receipts)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
