#!/usr/bin/env bash
set -euo pipefail
RUN_ID="${RUN_ID:-}"
RELAY=".opencode-relay.md"
FAIL=0
echo "----- VERIFICATION REPORT -----"
if [[ -f "$RELAY" ]]; then
  if [[ -n "$RUN_ID" ]] && ! grep -qx "run_id: $RUN_ID" "$RELAY"; then
    echo "FAIL: NOT COMPLETE -- relay is not for this run (expected run_id: $RUN_ID)"
    FAIL=1
  else
    echo "PASS: relay run_id matches this run"
  fi
  expected=$(ls */*.spec 2>/dev/null | wc -l)
  if [[ "$expected" -eq 0 ]]; then
    echo "FAIL: NOT COMPLETE -- no */*.spec found (run from repo root)"
    FAIL=1
  fi
  dep_rows=$(grep -c "deps-verified\|deps-fixed" "$RELAY" 2>/dev/null || true)
  dep_rows=${dep_rows:-0}
  echo "Inventory: $expected specs; dependency table rows: $dep_rows"
  if [[ "$dep_rows" -lt "$expected" ]]; then
    echo "FAIL: NOT COMPLETE -- dependency audit table has $dep_rows rows, need $expected (one per spec)"
    FAIL=1
  else
    echo "PASS: Dependency table: $dep_rows rows (>= $expected)"
  fi
  unproven_rows=$(grep -c "unproven:" "$RELAY" 2>/dev/null || true)
  unproven_rows=${unproven_rows:-0}
  echo "Correctness-contract rows: $unproven_rows (need $expected)"
  if [[ "$unproven_rows" -lt "$expected" ]]; then
    echo "FAIL: NOT COMPLETE -- $unproven_rows audit rows carry the unproven: contract, need $expected (one per spec)"
    FAIL=1
  else
    echo "PASS: Correctness contract present on $unproven_rows rows"
  fi
  spec_missing=$( { grep -L "resources/app-update\.yml" */*.spec 2>/dev/null || true; } | wc -l )
  spec_missing=${spec_missing:-0}
  if [[ "$spec_missing" -ne 0 ]]; then
    echo "FAIL: $spec_missing specs lack the in-app updater strip: $( { grep -L 'resources/app-update\.yml' */*.spec 2>/dev/null || true; } | tr '\n' ' ')"
    FAIL=1
  else
    echo "PASS: in-app updater strip present in all $expected specs"
  fi
  rules_gap=""
  for rules in */debian.rules; do
    [[ -f "$rules" ]] || continue
    pkgdir=$(dirname "$rules")
    if grep -qE 'payload/opt/|squashfs-root|linux-unpacked' "$rules" && ! grep -q "app-update\.yml" "$rules"; then
      rules_gap="$rules_gap $pkgdir"
    fi
  done
  if [[ -n "$rules_gap" ]]; then
    echo "FAIL: Electron Debian recipes missing the in-app updater strip:$rules_gap"
    FAIL=1
  else
    echo "PASS: Electron Debian recipes carry the in-app updater strip"
  fi
  if ! grep -qi "debian updater markers: 0" "$RELAY"; then
    echo "FAIL: NOT COMPLETE -- relay missing the Debian in-app updater marker sweep evidence (expects 'Debian updater markers: 0')"
    FAIL=1
  else
    echo "PASS: Debian in-app updater marker sweep recorded with zero markers"
  fi
  if ! grep -q "| package | packaged version |" "$RELAY"; then
    echo "FAIL: NOT COMPLETE -- version accuracy table (priority 2 deliverable) missing in relay"
    FAIL=1
  else
    echo "PASS: Version accuracy table present"
  fi
  for tool in "spec-cleaner" "rpmlint" "zypper"; do
    if ! grep -qi "$tool.*PASS\|PASS.*$tool" "$RELAY"; then
    echo "FAIL: NOT COMPLETE -- relay missing fresh evidence for $tool (with PASS result)"
    FAIL=1
  fi
  done
  if ! grep -qi "install-test table\|zypper install test" "$RELAY"; then
    echo "FAIL: install-test table missing in relay"
    FAIL=1
  else
    echo "PASS: Install-test table present"
  fi
  if ! grep -qi "DOCKER BATTLE TEST\|opensuse/tumbleweed\|zypper.*in" "$RELAY"; then
    echo "FAIL: NOT COMPLETE -- relay missing Docker battle test evidence"
    FAIL=1
  fi
else
  echo "FAIL: $RELAY missing"
  FAIL=1
fi
bad=0
for spec in */*.spec; do
  [[ -f "$spec" ]] || continue
  if ! grep -q "^Name:" "$spec" 2>/dev/null; then echo "FAIL: $spec missing Name:"; bad=$((bad+1)); fi
done
if [[ "$bad" -gt 0 ]]; then echo "FAIL: $bad specs malformed"; FAIL=1; fi

debdrift=$(python3 - <<'PY'
import glob, os, re, sys
def field(text, name):
    lines = text.splitlines()
    out, grab = [], False
    for ln in lines:
        if grab:
            out.append(ln.strip())
            grab = ln.rstrip().endswith(',')
            if not grab:
                break
            continue
        if ln.startswith(name + ':'):
            out.append(ln.split(':', 1)[1].strip())
            grab = ln.rstrip().endswith(',')
            if not grab:
                break
    return ' '.join(out)
def toks(s):
    return [t.strip() for t in s.replace('\n', ' ').split(',') if t.strip()]
bad = []
for dsc in sorted(glob.glob('*/*.dsc')):
    pkg = os.path.dirname(dsc)
    ctl = os.path.join(pkg, 'debian.control')
    spec = os.path.join(pkg, os.path.basename(pkg) + '.spec')
    d = open(dsc, encoding='utf-8', errors='replace').read()
    if not os.path.exists(ctl) or not os.path.exists(spec):
        continue
    c = open(ctl, encoding='utf-8', errors='replace').read()
    s = open(spec, encoding='utf-8', errors='replace').read()
    dsc_deps = toks(field(d, 'Build-Depends'))
    ctl_deps = toks(field(c, 'Build-Depends'))
    missing = [t for t in ctl_deps if t not in dsc_deps]
    if missing:
        bad.append(f'{pkg}: .dsc Build-Depends lacks {missing} (OBS installs only the .dsc list)')
    m = re.search(r'^Version:\s*(\S+)', s, re.M)
    dv = re.search(r'^Version:\s*(\S+)', d, re.M)
    if m and dv:
        ver = m.group(1)
        for mac in ('base_version', 'gitdate', 'shortcommit'):
            g = re.search(r'^%global\s+' + mac + r'\s+(\S+)', s, re.M)
            if g:
                ver = ver.replace('%{' + mac + '}', g.group(1))
        if not ver.startswith('%') and ver != dv.group(1):
            bad.append(f'{pkg}: .dsc Version {dv.group(1)} != spec Version {ver}')
    db = re.search(r'^Binary:\s*(\S+)', d, re.M)
    cp = re.search(r'^Package:\s*(\S+)', c, re.M)
    if db and cp and db.group(1) != cp.group(1):
        bad.append(f'{pkg}: .dsc Binary {db.group(1)} != debian.control Package {cp.group(1)}')
for b in bad:
    print(b)
PY
)
if [[ -n "$debdrift" ]]; then
  echo "FAIL: Debian recipe drift (3-target contract):"
  printf '%s\n' "$debdrift"
  FAIL=1
else
  echo "PASS: .dsc/debian.control/spec version+binary+Build-Depends agree for every Debian recipe"
fi

for tgt in "Tumbleweed" "Debian_Testing" "Debian_Unstable"; do
  if grep -qi "$tgt" "$RELAY" 2>/dev/null; then
    echo "PASS: relay mentions target $tgt"
  else
    echo "WARN: relay has no $tgt install evidence yet (3-target matrix - soft)"
  fi
done

if [[ "$FAIL" -ne 0 ]]; then echo "FAIL: NOT COMPLETE -- agent must continue working"; exit 1; fi
echo "PASS: VERIFICATION PASSED -- all $expected deps rows, version table, evidence, install+battle test present"
exit 0
