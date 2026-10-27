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
