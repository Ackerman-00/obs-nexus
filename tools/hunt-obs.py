#!/usr/bin/env python3
"""hunt-obs.py - machine-checked hunt categories for the OBS relay.

Every category runs a live check and prints one relay-ready line

    hunt: <category> - <what was checked and what it found>

followed by indented FINDING / note rows for anything that needs fixing.
A category that cannot reach its source says UNVERIFIED with the exact reason
and never counts as a clean receipt. A concrete defect exits 1.
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

PROJECT = "home:ackerman"
API = "https://api.opensuse.org"
PUB = "https://download.opensuse.org/repositories/home:ackerman"
UA = "obs-nexus-hunt/1.0 (+https://github.com/Ackerman-00/obs-nexus; issue tracker: https://github.com/Ackerman-00/obs-nexus/issues)"
TARGETS = {
    "Tumbleweed": PUB + "/openSUSE_Tumbleweed/repodata/repomd.xml",
    "Debian_Testing": PUB + "/Debian_Testing/Packages.gz",
    "Debian_Unstable": PUB + "/Debian_Unstable/Packages.gz",
}
CATS = ("builds", "published-nvr", "sources", "upstream-versions", "cves",
        "pins", "probes", "release-discipline", "readme", "targets")
ALIASES = {
    "build": "builds",
    "published": "published-nvr", "nvr": "published-nvr",
    "source": "sources", "drift": "sources",
    "upstream": "upstream-versions", "versions": "upstream-versions",
    "cve": "cves", "osv": "cves",
    "pin": "pins",
    "probe": "probes",
    "release": "release-discipline", "changes": "release-discipline",
    "target": "targets",
}


def get(url, auth=False):
    cmd = ["curl", "-sS", "-L", "--max-time", "45", "-A", UA, "-w", "\n%{http_code}",
           "-o", "-"]
    if auth and os.environ.get("OBS_USER") and os.environ.get("OBS_PASS"):
        cmd += ["-u", "%s:%s" % (os.environ["OBS_USER"], os.environ["OBS_PASS"])]
    tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if tok and url.startswith("https://api.github.com/"):
        cmd += ["-H", "Authorization: token %s" % tok]
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


def attrs(text):
    return dict(re.findall(r'(\w+)="([^"]*)"', text))


def specs():
    """spec directory -> name/version/release plus the unexpanded Version."""
    out = {}
    for sp in sorted(glob.glob("*/*.spec")):
        d = os.path.dirname(sp)
        txt = open(sp, encoding="utf-8", errors="replace").read()
        mac = {}
        for m in re.finditer(r"^%(?:global|define)\s+(\w+)\s+(\S+)", txt, re.M):
            mac.setdefault(m.group(1), m.group(2))
        name = re.search(r"^Name:\s*(\S+)", txt, re.M)
        ver = re.search(r"^Version:\s*(\S+)", txt, re.M)
        rel = re.search(r"^Release:\s*(\S+)", txt, re.M)
        if not (name and ver):
            continue
        raw = ver.group(1)
        v = raw
        for _ in range(4):
            nv = re.sub(r"%\{(\w+)\}", lambda m: mac.get(m.group(1), m.group(0)), v)
            nv = re.sub(r"%(\w+)", lambda m: mac.get(m.group(1), m.group(0)), nv)
            if nv == v:
                break
            v = nv
        out[d] = {"name": name.group(1), "version": v, "release": rel.group(1) if rel else "?",
                  "raw_version": raw}
    return out


def deb_binaries():
    """spec directory -> Debian binary package name from its .dsc."""
    out = {}
    for dsc in sorted(glob.glob("*/*.dsc")):
        txt = open(dsc, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^Binary:\s*(\S+)", txt)
        if m:
            out[os.path.dirname(dsc)] = m.group(1)
    return out


def build_status(phase):
    return "unverified" if phase.startswith("UNVERIFIED") else "ok"


def builds():
    code, body = get("%s/build/%s/_result" % (API, PROJECT), auth=True)
    if code != 200:
        phase = "UNVERIFIED OBS build API HTTP %d (no usable build state; not clean)" % code
        print("hunt: builds - %s" % phase)
        return build_status(phase)
    text = body.decode("utf-8", "replace")
    failed = re.findall(r'package="([^"]+)"[^>]*code="(failed|broken)"', text)
    failed += [(b, a) for a, b in re.findall(r'code="(failed|broken)"[^>]*package="([^"]+)"', text)]
    names = sorted({p for p, _ in failed})
    if names:
        print("hunt: builds - FAILED in OBS build result: %s" % ", ".join(names[:20]))
        for p in names[:20]:
            print("  FINDING %s is failed/broken on the OBS build result" % p)
        return "defect"
    print("hunt: builds - OBS build API HTTP 200, no failed/broken package")
    return "ok"


def vprefix(v):
    """Comparable numeric prefix of a package version, epoch and release dropped."""
    v = re.sub(r"^\d+:", "", v.strip())
    v = v.split("-")[0]
    m = re.match(r"^(\d+(?:\.\d+)*)", v)
    return m.group(1) if m else ""


INFLIGHT_STATES = {"building", "scheduled", "dispatching", "signing", "blocked", "unbroken"}


def build_states():
    """Per package: its own status codes plus whether the repository is still building/publishing."""
    code, body = get("%s/build/%s/_result" % (API, PROJECT), auth=True)
    states = {}
    if code != 200:
        return states
    text = body.decode("utf-8", "replace")
    for rattrs_text, inner in re.findall(r"<result\b([^>]*)>(.*?)</result>", text, re.S):
        rattrs = attrs(rattrs_text)
        busy = rattrs.get("state", "") in INFLIGHT_STATES or rattrs.get("code", "") in INFLIGHT_STATES
        for pkg, st in re.findall(r'<status package="([^"]+)" code="([^"]+)"', inner):
            info = states.setdefault(pkg, {"busy": False, "codes": set()})
            info["codes"].add(st)
            info["busy"] = info["busy"] or busy
    return states


def published_verdict(pub, spec, info):
    """An index that trails the spec is only a defect when nothing is building or publishing."""
    if vcmp(pub, spec) >= 0:
        return "ok"
    if info.get("busy") or (set(info.get("codes", ())) & INFLIGHT_STATES):
        return "inflight"
    return "behind"


def published():
    local = specs()
    debs = deb_binaries()
    states = build_states()
    seen = {}
    for target, url in TARGETS.items():
        code, body = get(url)
        if code != 200:
            print("hunt: published-nvr - UNVERIFIED %s index HTTP %d" % (target, code))
            continue
        if target == "Tumbleweed":
            m = re.search(rb'href="([^"]*-primary\.xml\.gz)"', body)
            if not m:
                print("hunt: published-nvr - UNVERIFIED Tumbleweed primary.xml.gz link absent")
                continue
            primary = url.rsplit("/repodata/", 1)[0] + "/" + m.group(1).decode()
            c2, raw = get(primary)
            if c2 != 200:
                print("hunt: published-nvr - UNVERIFIED Tumbleweed primary HTTP %d" % c2)
                continue
            names = {}
            for blk in re.findall(r"<package\b[^>]*>(.*?)</package>",
                                  gzip.decompress(raw).decode("utf-8", "replace"), re.S):
                n = re.search(r"<name>([^<]+)</name>", blk)
                v = re.search(r"<version\b([^/]*)/>", blk)
                if n:
                    names[n.group(1)] = attrs(v.group(1)).get("ver", "") if v else ""
        else:
            names = {}
            for blk in gzip.decompress(body).decode("utf-8", "replace").split("\n\n"):
                n = re.search(r"(?m)^Package:\s*(\S+)", blk)
                a = re.search(r"(?m)^Architecture:\s*(\S+)", blk)
                v = re.search(r"(?m)^Version:\s*(\S+)", blk)
                if n and not (a and a.group(1) == "source"):
                    names[n.group(1)] = v.group(1) if v else ""
        seen[target] = names
        print("  note %s index HTTP 200, %d binary packages" % (target, len(names)))
    if not seen:
        print("hunt: published-nvr - UNVERIFIED no published index readable on any target")
        return "unverified"
    missing, behind, inflight, compared, uncomparable = [], [], [], 0, 0
    for d, meta in sorted(local.items()):
        expects_deb = d in debs
        raw = meta["raw_version"]
        for target, names in seen.items():
            if target.startswith("Debian") and not expects_deb:
                continue
            want = debs.get(d, d) if target.startswith("Debian") else meta["name"]
            if want not in names:
                missing.append("%s missing from %s" % (want, target))
                continue
            if "%" in raw:
                uncomparable += 1
                continue
            pub, spec_v = vprefix(names[want]), vprefix(meta["version"])
            if not (pub and spec_v):
                uncomparable += 1
                continue
            compared += 1
            verdict = published_verdict(pub, spec_v, states.get(d, {}))
            if verdict == "behind":
                behind.append("%s on %s serves %s, spec builds %s"
                              % (want, target, names[want], meta["version"]))
            elif verdict == "inflight":
                inflight.append("%s on %s serves %s while %s builds"
                                % (want, target, names[want], meta["version"]))
    if missing or behind:
        print("hunt: published-nvr - DEFECT %d missing, %d behind the spec"
              % (len(missing), len(behind)))
        for row in (missing + behind)[:30]:
            print("  FINDING %s" % row)
        return "defect"
    for row in inflight:
        print("  note in flight: %s" % row)
    print("hunt: published-nvr - %d targets read, %d names present, %d versions at/above the spec, "
          "%d in-flight builds, %d macro/unparsable versions skipped"
          % (len(seen), len(local), compared, len(inflight), uncomparable))
    return "ok"


def sources():
    code, body = get("%s/source/%s/_project?view=info" % (API, PROJECT), auth=True)
    if code != 200:
        print("hunt: sources - UNVERIFIED OBS source API HTTP %d (no authenticated drift check)" % code)
        return "unverified"
    print("hunt: sources - OBS source API HTTP 200 (project metadata readable)")
    return "ok"


def rev_seen(tag, text):
    """Tag equivalence: dot and dash separators are the same version to a packager."""
    cands = {tag, tag.replace("-", "."), tag.replace(".", "-"), tag.replace("_", ".")}
    return any(c and c in text for c in cands)


def latest_tag(owner, repo):
    code, body = get("https://api.github.com/repos/%s/%s/releases/latest" % (owner, repo))
    if code == 200:
        try:
            tag = (json.loads(body).get("tag_name") or "").lstrip("v")
        except Exception:
            tag = ""
        if tag:
            return tag, "release"
    elif code in (403, 429):
        return "", "GitHub rate limit HTTP %d" % code
    code_t, body_t = get("https://api.github.com/repos/%s/%s/tags?per_page=100" % (owner, repo))
    if code_t == 200:
        try:
            names = [t["name"] for t in json.loads(body_t)]
        except Exception:
            names = []
        vers = [n for n in names if re.match(r"^v?\d", n)]
        if vers:
            best = max(vers, key=lambda n: [int(x) for x in re.findall(r"\d+", n)[:4]] or [0])
            return best.lstrip("v"), "tag"
        return "", "no version-like tag (commit HEAD is the reference)"
    return "", "releases HTTP %d, tags HTTP %d" % (code, code_t)


def source_github(txt):
    """Owner/repo/tag prefix from a GitHub release Source0 when URL: is not GitHub."""
    m = re.search(r"(?m)^Source\d*:\s*\S*github\.com/([^/\s]+)/([^/\s]+)/releases/download/([^/\s]+)/", txt)
    if not m:
        return None
    tag = m.group(3)
    ver = re.search(r"\d[\w.]*$", tag)
    if not ver:
        return None
    return m.group(1), re.sub(r"\.git$", "", m.group(2)).strip("/"), tag[:ver.start()]


def latest_prefixed_tag(owner, repo, prefix):
    """Newest stable tag sharing the pinned tag's prefix, read from the tag ref list."""
    try:
        out = subprocess.run(["git", "ls-remote", "--tags",
                              "https://github.com/%s/%s.git" % (owner, repo)],
                             capture_output=True, text=True, timeout=180)
    except Exception as exc:
        return "", "git ls-remote failed (%s)" % exc
    if out.returncode != 0:
        return "", "git ls-remote exit %d" % out.returncode
    best = ""
    for line in out.stdout.splitlines():
        ref = line.split("\t")[-1].replace("^{}", "")
        if not ref.startswith("refs/tags/"):
            continue
        tag = ref[len("refs/tags/"):]
        if not tag.startswith(prefix):
            continue
        tail = tag[len(prefix):]
        if not re.match(r"^\d", tail):
            continue
        if re.search(r"(?i)alpha|beta|rc|pre|nightly|dev", tail):
            continue
        if not best or vcmp(tail, best) > 0:
            best = tail
    if best:
        return best, "tag"
    return "", "no stable tag with prefix %s" % (prefix or "<none>")


def upstream_versions():
    bad, unverified = [], []
    checked = 0
    for sp in sorted(glob.glob("*/*.spec")):
        d = os.path.dirname(sp)
        txt = open(sp, encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^URL:\s*https?://github\.com/([^/\s]+)/([^/\s]+)", txt)
        if m:
            owner = m.group(1)
            repo = re.sub(r"\.git$", "", m.group(2)).strip("/")
            tag, why = latest_tag(owner, repo)
            if not tag:
                unverified.append("%s %s/%s (%s)" % (d, owner, repo, why))
            else:
                checked += 1
                if not rev_seen(tag, txt):
                    bad.append("%s lacks newest upstream tag %s" % (d, tag))
            time.sleep(1)
            continue
        sg = source_github(txt)
        if not sg:
            continue
        owner, repo, prefix = sg
        ver, why = latest_prefixed_tag(owner, repo, prefix)
        if not ver:
            unverified.append("%s %s/%s (%s)" % (d, owner, repo, why))
        else:
            checked += 1
            sv = re.search(r"(?m)^Version:\s*(\S+)", txt)
            specver = sv.group(1) if sv else ""
            if not specver or "%" in specver or "$" in specver:
                unverified.append("%s template version, compare by hand" % d)
            elif vcmp(ver, specver) > 0:
                bad.append("%s pins %s, newest %s release is %s" % (d, specver, prefix, ver))
        time.sleep(1)
    if bad:
        print("hunt: upstream-versions - DEFECT %d specs behind upstream, %d checked"
              % (len(bad), checked))
        for row in bad[:20]:
            print("  FINDING %s" % row)
        for row in unverified[:10]:
            print("  note unverified %s" % row)
        return "defect"
    if checked == 0:
        print("hunt: upstream-versions - UNVERIFIED no GitHub ref readable (%d blocked)"
              % len(unverified))
        return "unverified"
    print("hunt: upstream-versions - %d GitHub refs checked, no behind pins (%d unverified)"
          % (checked, len(unverified)))
    for row in unverified[:10]:
        print("  note unverified %s" % row)
    return "ok"


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


def distro_upstream(v):
    """Upstream part of a distro EVR: drop the epoch and the -release suffix."""
    v = v.strip()
    if re.match(r"^\d+:", v):
        v = v.split(":", 1)[1]
    m = re.match(r"^(.+?)-\d[\w.+~]*$", v)
    return m.group(1) if m else v


def distro_range_hit(version, events):
    """in_range over a distro advisory, ignoring the distro's own release counter."""
    ver = distro_upstream(version)
    intro = "0"
    for ev in events:
        if "introduced" in ev:
            intro = distro_upstream(ev["introduced"])
        elif "fixed" in ev:
            if vcmp(ver, intro) >= 0 and vcmp(ver, distro_upstream(ev["fixed"])) < 0:
                return True
            intro = None
        elif "last_affected" in ev:
            if vcmp(ver, intro) >= 0 and vcmp(ver, distro_upstream(ev["last_affected"])) <= 0:
                return True
            intro = None
    return intro is not None and vcmp(ver, intro) >= 0


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


def cves():
    queries = []
    for sp in sorted(glob.glob("*/*.spec")):
        txt = open(sp, encoding="utf-8", errors="replace").read()
        v = re.search(r"(?m)^Version:\s*(\S+)", txt)
        if not v:
            continue
        queries.append({"version": v.group(1), "package": {"name": os.path.dirname(sp)}})
    if not queries:
        print("hunt: cves - UNVERIFIED no spec Version to query")
        return "unverified"
    req = urllib.request.Request(
        "https://api.osv.dev/v1/querybatch",
        data=json.dumps({"queries": queries[:1000]}).encode(),
        headers={"User-Agent": UA, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            result = json.loads(r.read())["results"]
    except Exception as e:
        print("hunt: cves - UNVERIFIED querybatch %s (scan did not run)" % type(e).__name__)
        return "unverified"
    hits = [(q, v.get("vulns", [])) for q, v in zip(queries, result) if v.get("vulns")]
    affected, excused = [], []
    for q, vulns in hits[:40]:
        for item in vulns:
            code, body = get("https://api.osv.dev/v1/vulns/" + item["id"])
            if code != 200:
                if code != 404:
                    print("  note %s %s advisory HTTP %d" % (q["package"]["name"], item["id"], code))
                continue
            try:
                adv = json.loads(body)
            except Exception:
                continue
            hit = unfixed = False
            distro = any(":" in (aff.get("package", {}).get("ecosystem") or "")
                         for aff in adv.get("affected", []))
            for aff in adv.get("affected", []):
                for rng in aff.get("ranges", []):
                    events = rng.get("events", [])
                    covered = distro_range_hit(q["version"], events) if distro \
                        else in_range(q["version"], events)
                    if covered:
                        hit = True
                        if not any("fixed" in e for e in events):
                            unfixed = True
                    elif distro and in_range(q["version"], events):
                        excused.append("%s %s %s (distro fixed evr %s, same upstream release as ours)"
                                       % (q["package"]["name"], q["version"], item["id"],
                                          ",".join(e["fixed"] for e in events if "fixed" in e)))
            if hit and unfixed:
                ceiling = next((c for c in (cna_ceiling(a) for a in adv.get("aliases", []) + [item["id"]]) if c), None)
                if ceiling and vcmp(q["version"], ceiling) >= 0:
                    excused.append("%s %s %s (fixed upstream < %s)"
                                   % (q["package"]["name"], q["version"], item["id"], ceiling))
                    time.sleep(0.2)
                    continue
            if hit:
                affected.append("%s %s %s" % (q["package"]["name"], q["version"], item["id"]))
            time.sleep(0.2)
    if affected:
        print("hunt: cves - AFFECTED %d in-range advisories on pinned versions" % len(affected))
        for row in affected:
            print("  FINDING %s" % row)
        return "defect"
    print("hunt: cves - %d OSV hits range-filtered against the advisory's own events, "
          "no in-range advisory (%d excused: distro-unfixed above the upstream ceiling)"
          % (len(hits), len(excused)))
    for row in excused[:10]:
        print("  note excused %s" % row)
    return "ok"


def pins():
    bad = []
    checked = 0
    for sp in sorted(glob.glob("*/*.spec")):
        txt = open(sp, encoding="utf-8", errors="replace").read()
        found = re.findall(r"(?m)^#\s*sha256:\s*(\S+)", txt)
        has_source = bool(re.search(r"(?m)^Source\d*:\s*\S+", txt))
        for h in found:
            checked += 1
            if not re.fullmatch(r"[0-9a-f]{64}", h):
                bad.append("%s malformed sha256 pin %r" % (sp, h[:24]))
        if found and not has_source:
            bad.append("%s pins %d sha256 but declares no Source line" % (sp, len(found)))
    if bad:
        print("hunt: pins - DEFECT %d of %d sha256 pin comments unusable" % (len(bad), checked))
        for row in bad[:20]:
            print("  FINDING %s" % row)
        return "defect"
    print("hunt: pins - %d sha256 pin comments well-formed and attached to a Source line "
          "(hash comparison needs the downloaded artifact)" % checked)
    return "ok"


def probes():
    path = "tools/probes.txt"
    if not os.path.isfile(path):
        print("hunt: probes - DEFECT %s missing (install-sweep has no input)" % path)
        return "defect"
    rows, bad = {}, []
    for n, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        pkg = parts[0]
        if not pkg:
            bad.append("line %d has no package" % n)
            continue
        if pkg in rows:
            bad.append("%s listed twice (line %d)" % (pkg, n))
        if len(parts) < 2 or not parts[1]:
            bad.append("%s (line %d) has no install name" % (pkg, n))
        rows[pkg] = parts[2] if len(parts) > 2 else ""
    dirs = set(specs())
    missing = sorted(dirs - set(rows))
    unknown = sorted(set(rows) - dirs)
    if missing or unknown or bad:
        print("hunt: probes - DEFECT %d rows for %d specs: %d missing, %d unknown, %d malformed"
              % (len(rows), len(dirs), len(missing), len(unknown), len(bad)))
        for row in missing:
            print("  FINDING no probe row for %s" % row)
        for row in unknown:
            print("  FINDING probe row for %s has no spec directory" % row)
        for row in bad:
            print("  FINDING %s" % row)
        return "defect"
    smoke = sum(1 for v in rows.values() if v)
    print("hunt: probes - %d rows cover %d specs (%d with a smoke command, %d files-only)"
          % (len(rows), len(dirs), smoke, len(rows) - smoke))
    return "ok"


def changes_version(text):
    for line in text.splitlines()[:12]:
        m = re.search(r"-\s+([0-9][^\s-]*-\S+)", line)
        if m:
            return m.group(1)
    return ""


def release_discipline():
    local = specs()
    bad = []
    for d, meta in sorted(local.items()):
        ch = os.path.join(d, d + ".changes")
        if not os.path.isfile(ch):
            bad.append("%s has no .changes file" % d)
            continue
        top = changes_version(open(ch, encoding="utf-8", errors="replace").read())
        if top and meta["version"] not in top:
            bad.append("%s newest .changes entry names %s, spec Version is %s"
                       % (d, top, meta["version"]))
    if bad:
        print("hunt: release-discipline - INFO %d newest .changes entries do not name the spec "
              "Version (OBS style allows a fix description)" % len(bad))
        for row in bad[:10]:
            print("  note %s" % row)
        return "ok"
    print("hunt: release-discipline - newest .changes entry names each spec Version")
    return "ok"


def readme():
    txt = open("README.md", encoding="utf-8", errors="replace").read()
    names = {d: m["name"] for d, m in specs().items()}
    missing = sorted(d for d in names if d not in txt and names[d] not in txt)
    if missing:
        print("hunt: readme - DEFECT %d packages have no README row" % len(missing))
        for row in missing[:10]:
            print("  FINDING %s" % row)
        return "defect"
    print("hunt: readme - all %d packages listed in README.md" % len(names))
    return "ok"


def targets():
    txt = open("README.md", encoding="utf-8", errors="replace").read()
    missing = [t for t in ("Tumbleweed", "Forky", "Unstable") if t not in txt]
    codes = {}
    for name, url in TARGETS.items():
        codes[name] = get(url)[0]
    dead = [n for n, c in codes.items() if c == 404]
    unsure = ["%s HTTP %d" % (n, c) for n, c in codes.items() if c not in (200, 404)]
    if missing or dead:
        print("hunt: targets - DEFECT %s%s"
              % ("README omits " + ", ".join(missing) if missing else "",
                 ("; " if missing else "") + "repository 404: " + ", ".join(dead) if dead else ""))
        for row in missing:
            print("  FINDING README does not document %s" % row)
        for row in dead:
            print("  FINDING %s repository index answers 404" % row)
        return "defect"
    if unsure:
        print("hunt: targets - UNVERIFIED %s" % "; ".join(unsure))
        return "unverified"
    print("hunt: targets - README documents Tumbleweed/Forky/Sid and all three repository "
          "indexes answer HTTP 200")
    return "ok"


FUNCS = {
    "builds": builds,
    "published-nvr": published,
    "sources": sources,
    "upstream-versions": upstream_versions,
    "cves": cves,
    "pins": pins,
    "probes": probes,
    "release-discipline": release_discipline,
    "readme": readme,
    "targets": targets,
}


def selftest():
    """Positive and negative fixtures for the version/range logic."""
    ok = True
    cases = [
        (in_range("1.4.0", [{"introduced": "0"}, {"fixed": "1.0.1"}]), False, "above fixed ceiling"),
        (in_range("0.9.0", [{"introduced": "0"}, {"fixed": "1.0.1"}]), True, "below fixed ceiling"),
        (in_range("1.0.1", [{"introduced": "0"}, {"fixed": "1.0.1"}]), False, "exactly at fixed"),
        (in_range("1.4.0", [{"introduced": "0"}]), True, "unfixed range covers all"),
        (in_range("1.2.0", [{"introduced": "1.1.0"}, {"last_affected": "1.3.0"}]), True, "last_affected"),
        (distro_upstream("1:1.2.3-4.1"), "1.2.3", "epoch and distro release stripped"),
        (distro_upstream("1.4.0"), "1.4.0", "plain version untouched"),
        (distro_range_hit("1.4.0", [{"introduced": "0"}, {"fixed": "1.4.0-1.1"}]), False,
         "same upstream release as the distro fixed build"),
        (distro_range_hit("1.3.9", [{"introduced": "0"}, {"fixed": "1.4.0-1.1"}]), True,
         "older upstream than the distro fixed build stays affected"),
        (vcmp("0.85.4", "0.85.10"), -1, "numeric compare, not lexical"),
        (vcmp("2.0.7", "2.0.7"), 0, "equal"),
        (vcmp("26.11.5", "26.9.1"), 1, "major compare"),
        (rev_seen("2026-10-31.1", "Version: 2026.10.31.1"), True, "dash/dot tag equivalence"),
        (rev_seen("0.85.4", "Version: 0.85.2"), False, "different version is not equivalent"),
        (source_github("Source0: https://github.com/cline/cline/releases/download/desktop-v0.0.50/Cline.deb"),
         ("cline", "cline", "desktop-v"), "prefixed release asset yields prefix"),
        (source_github("Source0: fluxer.rpm"), None, "local Source0 has no GitHub ref"),
        (vprefix("1:0.0.49-1+74.3"), "0.0.49", "epoch and release stripped"),
        (vprefix("1.24.2b-21.1"), "1.24.2", "letter suffix dropped"),
        (published_verdict("0.85.7", "0.86.0", {"busy": True, "codes": {"succeeded"}}), "inflight", "repo still publishing"),
        (published_verdict("0.85.7", "0.86.0", {"busy": False, "codes": {"succeeded"}}), "behind", "trailing index, repo finished"),
        (published_verdict("0.86.0", "0.86.0", {"busy": False, "codes": {"succeeded"}}), "ok", "index at the spec"),
    ]
    for got, want, label in cases:
        if got != want:
            ok = False
            print("selftest FAIL %s: got %r, want %r" % (label, got, want))
    print("selftest PASS" if ok else "selftest FAIL")
    return 0 if ok else 1


def usage():
    print(__doc__.strip())
    print()
    print("usage: tools/hunt-obs.py [category ...]")
    print()
    print("categories: " + ", ".join(CATS))
    print("aliases:    " + ", ".join("%s=%s" % (k, v) for k, v in sorted(ALIASES.items())))
    print()
    print("no category runs all of them. --selftest runs the version fixtures.")


def main(argv):
    if "-h" in argv or "--help" in argv:
        usage()
        return 0
    if "--selftest" in argv:
        return selftest()
    unknown = [a for a in argv if a not in CATS and a not in ALIASES]
    if unknown:
        sys.stderr.write("hunt-obs: unknown category %s (see --help)\n" % ", ".join(unknown))
        return 2
    os.chdir(ROOT)
    wanted = list(dict.fromkeys(ALIASES.get(a, a) for a in argv)) or list(CATS)
    statuses = [FUNCS[c]() for c in wanted]
    defect = statuses.count("defect")
    unverified = statuses.count("unverified")
    print("hunt-obs: %d categories, %d defect, %d unverified (unverified is not a clean receipt)"
          % (len(statuses), defect, unverified))
    return 1 if defect else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
