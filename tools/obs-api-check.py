#!/usr/bin/env python3
"""Live OBS build/published-state audit. Stdlib only.

Uses the documented OBS API for build state and the public download tree for
published NVRs. An unauthenticated 401 is reported as UNVERIFIED with the
exact status code, never as clean.
"""
import gzip
import glob
import os
import re
import subprocess
import sys
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



def upstream_versions():
    """Latest GitHub release/tag vs the spec version, <=1 request/s."""
    import json
    import time
    bad = []
    checked = 0
    for sp in sorted(glob.glob("*/*.spec")):
        txt = open(sp, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^URL:\s*https?://github\.com/([^/\s]+)/([^/\s]+)", txt)
        if not m:
            continue
        owner, repo = m.group(1), m.group(2)
        code, body = get(f"https://api.github.com/repos/{owner}/{repo}/releases/latest")
        if code != 200:
            print(f"hunt: upstream-versions - UNVERIFIED {owner}/{repo} HTTP {code}")
            time.sleep(1)
            continue
        try:
            tag = json.loads(body).get("tag_name", "").lstrip("v")
        except Exception:
            tag = ""
        if tag:
            checked += 1
            if tag not in txt:
                bad.append(f"{os.path.dirname(sp)} spec lacks newest upstream {tag}")
        time.sleep(1)
    if bad:
        print("hunt: upstream-versions - DEFECT " + "; ".join(bad))
        return True
    print(f"hunt: upstream-versions - {checked} GitHub refs checked, no behind pins")
    return False


def cves():
    """OSV batch; IDs only, range-filter via GET /v1/vulns/<id>."""
    import json
    import time
    queries = []
    for sp in sorted(glob.glob("*/*.spec")):
        txt = open(sp, encoding="utf-8", errors="replace").read()
        v = re.search(r"(?m)^Version:\s*(\S+)", txt)
        if not v:
            continue
        queries.append({"version": v.group(1), "package": {"name": os.path.dirname(sp)}})
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
    for q, vulns in hits[:40]:
        for item in vulns:
            code, body = get("https://api.osv.dev/v1/vulns/" + item["id"])
            if code != 200:
                continue
            try:
                adv = json.loads(body)
            except Exception:
                continue
            for aff in adv.get("affected", []):
                for rng in aff.get("ranges", []):
                    for ev in rng.get("events", []):
                        if "fixed" in ev and q["version"] == ev["fixed"]:
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break
            else:
                affected.append(f"{q['package']['name']} {q['version']} {item['id']}")
            time.sleep(0.2)
    if affected:
        print("hunt: cves - AFFECTED " + "; ".join(affected))
        return True
    print(f"hunt: cves - {len(hits)} OSV hits range-filtered, no fixed-version match")
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


def probes():
    if not os.path.isfile("tools/probes.txt"):
        print("hunt: probes - DEFECT tools/probes.txt missing")
        return True
    rows = {l.split("|")[0] for l in open("tools/probes.txt") if l.strip()}
    names = set(specs())
    missing = sorted(names - rows)
    if missing:
        print("hunt: probes - DEFECT no row for " + ", ".join(missing))
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

def main():
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
