#!/bin/bash
set -u
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT" || exit 1
[ $# -ge 1 ] || { echo "usage: $0 <pkg> [pkg ...]" >&2; exit 2; }
: "${OBS_USER:?OBS_USER unset}"
: "${OBS_PASS:?OBS_PASS unset}"
API=https://api.opensuse.org/source/home:ackerman
fail=0
for pkg in "$@"; do
  echo "=== SYNC $pkg ==="
  [ -d "$pkg" ] || { echo "  no such dir"; fail=1; continue; }
  remote=$(curl -s -u "$OBS_USER:$OBS_PASS" "$API/$pkg" | grep -oE '<entry name="[^"]+"' | sed 's/.*name="//;s/"$//' | grep -v '^_')
  for f in "$pkg"/*; do
    [ -f "$f" ] || continue
    bn=$(basename "$f")
    [ "$bn" = "update.sh" ] && continue
    code=$(curl -s -o /dev/null -w '%{http_code}' -u "$OBS_USER:$OBS_PASS" -T "$f" "$API/$pkg/$bn")
    echo "  PUT $bn -> HTTP $code"
    [ "$code" = "200" ] || fail=1
  done
  for f in $remote; do
    [ -f "$pkg/$f" ] && continue
    case "$f" in
      *.spec|*.changes|*.dsc|debian.*|_service|*.rpmlintrc|*.desktop|*.patch|*.py) ;;
      *) echo "  keep remote artifact $f (generated/downloaded, not repo-managed)"; continue ;;
    esac
    code=$(curl -s -o /dev/null -w '%{http_code}' -u "$OBS_USER:$OBS_PASS" -X DELETE "$API/$pkg/$f")
    echo "  DELETE stale $f -> HTTP $code"
    [ "$code" = "200" ] || fail=1
  done
  if [ -f "$pkg/_service" ]; then
    code=$(curl -s -o /dev/null -w '%{http_code}' -u "$OBS_USER:$OBS_PASS" -X POST "$API/$pkg?cmd=runservice")
    echo "  runservice -> HTTP $code"
  else
    code=$(curl -s -o /dev/null -w '%{http_code}' -u "$OBS_USER:$OBS_PASS" -X POST "$API/$pkg?cmd=rebuild")
    echo "  rebuild -> HTTP $code"
  fi
  [ "$code" = "200" ] || fail=1
done
exit $fail
