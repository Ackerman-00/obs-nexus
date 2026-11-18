#!/usr/bin/env bash
set -uo pipefail
RUN_ID="${RUN_ID:-}"
RELAY="${RELAY:-.opencode-relay.md}"
FAIL=0
echo "----- VERIFICATION REPORT -----"
fail() { echo "FAIL: $1"; FAIL=1; }
pass() { echo "PASS: $1"; }
[[ -f "$RELAY" ]] || { fail "$RELAY missing"; echo "FAIL: NOT COMPLETE -- agent must continue working"; exit 1; }
content=$(cat "$RELAY")
if [[ -n "$RUN_ID" ]]; then
  grep -qx "run_id: $RUN_ID" <<< "$content" || fail "relay is not for this run (expected run_id: $RUN_ID)"
  content=$(printf '%s\n' "$content" | awk -v id="run_id: $RUN_ID" '$0==id{f=1;next} f&&/^run_id: /{exit} f')
else
  pass "RUN_ID not set - checking whole relay"
fi
grep -qix "status: complete" <<< "$content" && pass "status: complete" || fail "no anchored status: complete in this run"

expected=$(ls */*.spec 2>/dev/null | wc -l)
[[ "$expected" -gt 0 ]] || fail "no */*.spec found (run from repo root)"
grep -q "| package | upstream deps evidence |" <<< "$content" && pass "dependency audit table header" || fail "dependency audit table header missing"
dep_rows=$(printf '%s' "$content" | grep -oE "^\| [a-zA-Z0-9._+-]+ \|.*\| (deps-verified|deps-fixed|version-checked|retired-stub)\b" | awk -F'|' '{gsub(/ /,"",$2); print $2}' | sort -u | wc -l || true)
unproven_rows=$(printf '%s' "$content" | grep -oE "^\| [a-zA-Z0-9._+-]+ \|.*unproven:" | awk -F'|' '{gsub(/ /,"",$2); print $2}' | sort -u | wc -l || true)
[[ "$dep_rows" -ge "$expected" ]] && pass "dependency table $dep_rows rows (>= $expected)" || fail "dependency table has $dep_rows rows, need $expected"
[[ "$unproven_rows" -ge "$expected" ]] && pass "correctness contract on $unproven_rows rows" || fail "unproven: contract on $unproven_rows rows, need $expected"

for tool in "spec-cleaner" "rpmlint" "zypper"; do
  grep -qi "$tool.*PASS\|PASS.*$tool" <<< "$content" && pass "tool evidence $tool" || fail "missing fresh PASS evidence for $tool"
done
grep -q "| package | packaged version |" <<< "$content" && pass "version accuracy table header" || fail "version accuracy table header missing"
grep -qi "debian updater markers: 0" <<< "$content" && pass "Debian updater markers: 0" || fail "missing 'Debian updater markers: 0'"
grep -qi "DOCKER BATTLE TEST\|opensuse/tumbleweed\|zypper.*in" <<< "$content" && pass "Docker battle test evidence" || fail "missing Docker battle test evidence"

spec_missing=$( { grep -L "resources/app-update\.yml" */*.spec 2>/dev/null || true; } | wc -l )
[[ "$spec_missing" -eq 0 ]] && pass "in-app updater strip present in all specs" || fail "$spec_missing specs lack the in-app updater strip"
rules_gap=""
for rules in */debian.rules; do
  [[ -f "$rules" ]] || continue
  if grep -qE 'payload/opt/|squashfs-root|linux-unpacked' "$rules" && ! grep -q "app-update\.yml" "$rules"; then rules_gap="$rules_gap $rules"; fi
done
[[ -z "$rules_gap" ]] && pass "Electron Debian recipes carry the updater strip" || fail "Debian recipes missing updater strip:$rules_gap"

today=$(date -u +%F); yest=$(date -u -d yesterday +%F 2>/dev/null || date -u -v-1d +%F)
g_decl=$(grep -ciE "^[[:space:]]*([-*][[:space:]]*)?((GAP|HOLD)[[:space:]]*:|not verified\b)" <<< "$content" || true)
g_head=$(grep -ciE "^[[:space:]]*([-*][[:space:]]*)?((GAP|HOLD)[[:space:]]*:|not verified\b)[^:]*:[[:space:]]*$" <<< "$content" || true)
g_cls=$(grep -ciE "^[[:space:]]*([-*][[:space:]]*)?((GAP|HOLD)[[:space:]]*:[[:space:]]*(external|actionable|none|nothing|n/a)\b|not verified\b.*\b(external|actionable)\b)" <<< "$content" || true)
g_act=$(grep -ciE "^[[:space:]]*([-*][[:space:]]*)?((GAP|HOLD)[[:space:]]*:[[:space:]]*actionable|not verified\b.*\bactionable\b)" <<< "$content" || true)
g_unclass=$(( g_decl - g_head - g_cls )); [[ "$g_unclass" -lt 0 ]] && g_unclass=0
[[ "$g_act" -eq 0 ]] || fail "actionable GAP present - the work is yours, do it"
[[ "$g_unclass" -eq 0 ]] || fail "$g_unclass gap(s) not classified external/actionable"
g_ext=$(grep -ciE "^[[:space:]]*([-*][[:space:]]*)?(GAP|HOLD): external" <<< "$content" || true)
g_probe=$(grep -ciE "^[[:space:]]*([-*][[:space:]]*)?(GAP|HOLD): external.*\[probe:" <<< "$content" || true)
[[ "$g_ext" -eq "$g_probe" ]] || fail "external GAP without [probe: token] ($g_ext declarations, $g_probe probes)"
g_noreason=$(grep -ciE "^[[:space:]]*([-*][[:space:]]*)?((GAP|HOLD)[[:space:]]*:[[:space:]]*external|not verified\b.*\bexternal\b)[[:space:]]*:?[[:space:]]*$" <<< "$content" || true)
[[ "$g_noreason" -eq 0 ]] || fail "external GAP with no reason"

it_rows=$(printf '%s' "$content" | awk -F'|' '
  /^\|/ {
    n = split($0, a, "|"); if (n < 3) next;
    verdict = "";
    for (i = 2; i <= n; i++) {
      c = a[i]; gsub(/^[ \t]+|[ \t]+$/, "", c); lc = tolower(c);
      if (lc == "fail" || lc == "broken" || lc ~ /^broken[-_(]/) { verdict = "FAIL"; continue }
      if (lc == "external" || lc == "blocked" || lc ~ /^blocked[-_(]/) { if (verdict != "FAIL") verdict = "EXTERNAL"; continue }
      if (verdict == "FAIL" || verdict == "EXTERNAL") continue
      if (lc == "pass" || lc == "ok" || lc == "installable" || lc == "fixed") { verdict = "PASS"; continue }
    }
    if (verdict == "") next;
    pkg = a[2]; gsub(/^[ \t]+|[ \t]+$/, "", pkg);
    if (pkg == "" || pkg == "package") next;
    printf "%s %s\n", pkg, verdict;
  }' | sort -u)
it_fail=$(grep -c ' FAIL$' <<< "$it_rows" || true)
it_pass=$(grep -c ' PASS$' <<< "$it_rows" || true)
[[ "$it_fail" -eq 0 ]] || fail "$it_fail install-test FAIL verdict(s): $(grep ' FAIL$' <<< "$it_rows" | tr '\n' ' ')"
[[ $(( it_fail + it_pass )) -ge 10 ]] || fail "only $(( it_fail + it_pass )) install-test rows, need >= 10"
changed_line=$(grep -m1 -E "^[[:space:]]*changed:" <<< "$content" || true)
[[ -n "$changed_line" ]] || fail "changed: token missing"
changed_pkgs=$(printf '%s' "$changed_line" | sed -E 's/^[[:space:]]*changed:[[:space:]]*//')
for cpkg in $changed_pkgs; do
  if ! grep -qx "$cpkg PASS" <<< "$it_rows"; then
    if grep -qx "$cpkg EXTERNAL" <<< "$it_rows" && grep -qiE "GAP: external.*$cpkg" <<< "$content"; then continue; fi
    fail "changed package $cpkg has no install-test PASS row"
  fi
done
for it_pkg in $(awk '{print $1}' <<< "$it_rows"); do
  if grep -qiE "$it_pkg.*(install|zypper).*PASS" <<< "$content" && grep -qx "$it_pkg FAIL" <<< "$it_rows"; then fail "contradiction: $it_pkg FAIL row next to install PASS"; fi
done
for dpkg in $(awk '$2=="EXTERNAL"{print $1}' <<< "$it_rows"); do
  grep -qiE "GAP: external.*$dpkg" <<< "$content" || fail "EXTERNAL row $dpkg has no GAP: external line"
done

d_found=$(grep -oE '^[[:space:]]*defects-found:[[:space:]]*[0-9]+' <<< "$content" | tail -1 | grep -oE '[0-9]+' || true)
d_fixed=$(grep -oE '^[[:space:]]*defects-fixed:[[:space:]]*[0-9]+' <<< "$content" | tail -1 | grep -oE '[0-9]+' || true)
[[ -n "$d_found" && -n "$d_fixed" ]] || fail "defects-found / defects-fixed missing"
[[ "$d_fixed" -ge "$d_found" ]] || [[ $(( d_fixed + g_decl )) -ge "$d_found" ]] || fail "defects-fixed $d_fixed < defects-found $d_found with $g_decl gaps"
hunt_cats=$(grep -oE '^[[:space:]]*hunt: [a-z0-9-]+' <<< "$content" | sort -u | wc -l || true)
[[ "$hunt_cats" -ge 8 ]] || fail "only $hunt_cats hunt categories, need >= 8"
web_line=$(grep -m1 -E "^[[:space:]]*websearch: .*($today|$yest)" <<< "$content" || true)
[[ -n "$web_line" ]] && grep -qiE 'https?://' <<< "$web_line" && pass "websearch receipt dated $today/$yest with URL" || fail "websearch: token missing, stale or URL-less"
skills_line=$(grep -m1 -E "^[[:space:]]*skills:" <<< "$content" || true)
[[ -n "$skills_line" ]] || fail "skills: token missing"
skills_n=$(printf '%s\n' "$skills_line" | grep -oE '\b(web-research|linux-packaging|rpm-copr|security-audit|code-review|systematic-debugging|verification-before-completion|github-ops|container-validation|python-tooling|writing-for-agents|fedora-triage|repo-improvement|why-from-record)\b' | sort -u | wc -l || true)
[[ "$skills_n" -ge 14 ]] || fail "skills: names only $skills_n of 14 ids"
for cpkg in $changed_pkgs; do
  grep -qE "^[[:space:]]*plan: $cpkg " <<< "$content" || fail "changed package $cpkg missing plan: line"
  grep -qE "^[[:space:]]*deps: $cpkg " <<< "$content" || fail "changed package $cpkg missing deps: line"
  grep -qE "^[[:space:]]*artifact: $cpkg " <<< "$content" || fail "changed package $cpkg missing artifact: line"
done
grep -qE '^[[:space:]]*deps: .*(Cargo\.toml|meson\.build|CMakeLists\.txt|go\.mod|pyproject\.toml|https?://|\.spec)' <<< "$content" || fail "deps: line has no upstream build file"
for field in 'https?://' 'format:' 'upstream-deps:' 'improvements:'; do
  grep -qE "^[[:space:]]*artifact: .*$field" <<< "$content" || fail "artifact: line missing $field"
done
improve_line=$(grep -m1 -E '^[[:space:]]*improve: [0-9]+ ' <<< "$content" || true)
[[ -n "$improve_line" ]] || fail "improve: token missing"
improve_n=$(printf '%s\n' "$improve_line" | sed -E 's/^[[:space:]]*improve: ([0-9]+).*/\1/')
[[ "$improve_n" -ge 5 ]] || fail "improve: has $improve_n candidates, need >= 5"
grep -qE 'landed:[[:space:]]*[0-9a-f]{7,40}|issue[[:space:]]*#[0-9]+' <<< "$improve_line" || fail "improve: missing landed: commit/issue"
why_line=$(grep -m1 -E '^[[:space:]]*why: .*source:' <<< "$content" || true)
[[ -n "$why_line" ]] && grep -qE '[0-9a-f]{7,40}|AGENTS\.md#|issue[[:space:]]*#[0-9]+|relay[[:space:]]+[0-9]+' <<< "$why_line" && pass "why: source cited" || fail "why: token missing or source uncited"
wait_line=$(grep -im1 -E '^[[:space:]]*([-*][[:space:]]*)?(needs-owner|waiting for (the )?owner|awaiting (the )?owner|pending owner|owner approval|human approval|needs approval|owner to apply|requires owner)' <<< "$content" || true)
[[ -z "$wait_line" ]] || fail "owner-approval wait language present"
owner_ask=$(grep -im1 -E 'needs[[:space:]]*-?[[:space:]]*owner|wait(ing)? for (the )?owner|ask(ing)? (the )?owner|(approv|permission|decision).{0,20}from (the )?owner|owner.{0,12}(must|needs to|has to) (approv|decid)|owner declined|awaiting (the )?owner' <<< "$content" || true)
[[ -z "$owner_ask" ]] || fail "owner-approval ask language present"

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
