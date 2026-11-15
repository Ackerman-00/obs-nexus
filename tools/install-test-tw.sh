#!/bin/bash
set -u
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT" || exit 1
[ $# -ge 1 ] || { echo "usage: $0 <pkg> [pkg ...]" >&2; exit 2; }
IMG=registry.opensuse.org/opensuse/tumbleweed:latest
fail=0
for pkg in "$@"; do
  echo "=== TW INSTALL $pkg ==="
  out=$(docker run --rm "$IMG" bash -lc '
    set -u
    zypper --non-interactive --gpg-auto-import-keys addrepo --refresh https://download.opensuse.org/tumbleweed/repo/oss/ oss >/dev/null 2>&1
    zypper --non-interactive --gpg-auto-import-keys addrepo --refresh https://download.opensuse.org/repositories/home:ackerman/openSUSE_Tumbleweed/ nexus >/dev/null 2>&1
    zypper --non-interactive --gpg-auto-import-keys refresh >/dev/null 2>&1
    zypper --non-interactive install --no-recommends '"$pkg"' >/tmp/i.log 2>&1 || { echo INSTALL_FAIL; grep -E "Problem|nothing provides|not found" /tmp/i.log | head -5; exit 1; }
    echo INSTALL_OK
    rpm -q '"$pkg"' | head -1
    echo "updater_markers=$(find /opt /usr/share /usr/lib -maxdepth 6 \( -name app-update.yml -o -name package-type \) 2>/dev/null | wc -l)"
    for b in $(rpm -ql '"$pkg"' | grep -E "^/usr/bin/|^/opt/" | while read -r f; do [ -f "$f" ] && [ -x "$f" ] && head -c4 "$f" 2>/dev/null | grep -q ELF && echo "$f"; done | head -3); do
      miss=$(ldd "$b" 2>/dev/null | grep -c "not found")
      echo "ldd_missing=$miss ($b)"
      timeout 20 "$b" --version >/tmp/s.log 2>&1; rc=$?
      echo "smoke_rc=$rc ($b): $(head -1 /tmp/s.log | cut -c1-90)"
    done
    exit 0
  ' 2>&1)
  rc=$?
  printf '%s\n' "$out" | sed 's/^/  /'
  if [ "$rc" != 0 ] || printf '%s' "$out" | grep -q INSTALL_FAIL; then echo "=== RESULT $pkg FAIL"; fail=1; else echo "=== RESULT $pkg PASS"; fi
done
exit $fail
