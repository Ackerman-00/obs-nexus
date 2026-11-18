#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
GOOD="$TMP/relay.md"
expected=$(ls */*.spec 2>/dev/null | wc -l)
today=$(date -u +%F)

make_good() {
  cat > "$GOOD" <<EOF
run_id: 999
## run 999
status: complete
| package | upstream deps evidence | in spec (BR/Req) | missing | status |
|---|---|---|---|---|
EOF
  for spec in */*.spec; do
    pkg=$(basename "$(dirname "$spec")")
    printf '| %s | resolved live | BR=1 | none | deps-verified — unproven: not exercised |\n' "$pkg" >> "$GOOD"
  done
  cat >> "$GOOD" <<EOF
| package | packaged version | upstream reference (read live this run) | verdict |
|---|
spec-cleaner PASS rpmlint PASS zypper PASS
debian updater markers: 0
DOCKER BATTLE TEST opensuse/tumbleweed zypper in PASS
GAP: none
install-test table
| package | version tested | Tumbleweed | Debian_Testing | Debian_Unstable | markers | ldd |
|---|---|---|---|---|---|---|
EOF
  for i in $(seq 1 12); do
    printf '| probe%s | 1.0 | PASS | PASS | PASS | 0 | 0 |\n' "$i" >> "$GOOD"
  done
  cat >> "$GOOD" <<EOF
changed: probe1
plan: probe1 - probes run before edit
deps: probe1 - Cargo.toml compared with spec BuildRequires
artifact: probe1 - url: https://example.com/src.tar.gz format: tar upstream-deps: none improvements: none
defects-found: 2
defects-fixed: 2
websearch: 3 queries, 3 URLs, $today https://example.com
why: fix - source: abc1234 - inference: none
improve: 5 candidates - top pick - landed: abc1234
hunt: builds - ran
hunt: chroots - ran
hunt: upstream-versions - ran
hunt: cves - ran
hunt: pins - ran
hunt: probes - ran
hunt: published-nvr - ran
hunt: targets - ran
EOF
}

run_case() {
  local name="$1" expect="$2" rc
  RUN_ID=999 RELAY="$GOOD" bash tools/verify-opensuse.sh >"$TMP/out" 2>&1
  rc=$?
  if [ "$expect" = pass ]; then
    if [ "$rc" -eq 0 ]; then echo "OK   $name accepted"; else echo "FAIL $name rejected (expected accept)"; grep '^FAIL' "$TMP/out" | head -2; FAILED=1; fi
  else
    if [ "$rc" -ne 0 ]; then echo "OK   $name rejected"; else echo "FAIL $name accepted (expected reject)"; FAILED=1; fi
  fi
}

FAILED=0
make_good
run_case "well-formed relay" pass

make_good; sed -i 's/| probe1 | 1.0 | PASS/| probe1 | 1.0 | FAIL/' "$GOOD"
run_case "FAIL verdict cell" fail

make_good; sed -i 's/| probe2 | 1.0 | PASS | PASS | PASS | 0 | 0 |/| probe2 | 1.0 | FAIL | PASS | PASS | 0 | 0 |/' "$GOOD"
run_case "FAIL in one of three target cells" fail

make_good; sed -i '/^changed:/d' "$GOOD"
run_case "missing changed token" fail

make_good; echo 'GAP: something is wrong' >> "$GOOD"
run_case "unclassified gap" fail

make_good; echo 'GAP: actionable - fix the spec' >> "$GOOD"
run_case "actionable gap" fail

make_good; echo 'GAP: external - upstream 404' >> "$GOOD"
run_case "external gap without probe" fail

make_good; first_pkg=$(basename "$(dirname "$(ls */*.spec | head -1)")"); grep -v "^| $first_pkg |" "$GOOD" > "$TMP/g" && mv "$TMP/g" "$GOOD"
run_case "dependency row count short" fail

make_good; sed -i '/^defects-found:/d' "$GOOD"
run_case "missing defects-found" fail

make_good; sed -i '0,/^hunt: /d' "$GOOD"
run_case "only seven hunt categories" fail

make_good; sed -i "s/websearch: 3 queries, 3 URLs, $today/websearch: 3 queries, 3 URLs, 2000-01-01/" "$GOOD"
run_case "stale websearch date" fail

make_good; sed -i 's/ format: tar//' "$GOOD"
run_case "artifact without format field" fail

make_good; echo 'needs-owner approval to continue' >> "$GOOD"
run_case "owner approval wait" fail

make_good; sed -i 's/^status: complete/status: unfinished/' "$GOOD"
run_case "status not complete" fail

if [ "$FAILED" -ne 0 ]; then
  echo "FAIL: verifier self-test found a hole"
  exit 1
fi
echo "PASS: verifier self-test ($expected specs, 14 cases) stopped every forged relay"
exit 0
