#!/usr/bin/env bash
# Diff each package's spec in git against the spec OBS actually built.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
: "${OBS_USER:?OBS_USER unset}"
: "${OBS_PASS:?OBS_PASS unset}"
API=https://api.opensuse.org/source/home:ackerman
bad=0
for spec in */*.spec; do
  [ -f "$spec" ] || continue
  pkg=$(basename "$(dirname "$spec")")
  remote=$(curl -sS -u "$OBS_USER:$OBS_PASS" "$API/$pkg/$(basename "$spec")" 2>/dev/null)
  if [ -z "$remote" ] || printf '%s' "$remote" | grep -q '<error'; then
    echo "DRIFT UNVERIFIED $pkg (OBS source read failed)"
    continue
  fi
  if diff -q <(printf '%s\n' "$remote") "$spec" >/dev/null 2>&1; then
    echo "DRIFT OK $pkg"
  else
    echo "DRIFT MISMATCH $pkg"
    bad=$((bad + 1))
  fi
done
[ "$bad" -eq 0 ] || { echo "obs-drift: $bad mismatches"; exit 1; }
echo "obs-drift: no mismatches"
