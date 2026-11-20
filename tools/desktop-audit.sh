#!/usr/bin/env bash
# Resolve every shipped .desktop entry in a published package.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
case "${1:-}" in -h|--help) usage=1 ;; esac
if [ $# -lt 1 ] || [ "${usage:-0}" = 1 ]; then
  echo "usage: $0 <pkg> [tumbleweed|testing|sid]"
  echo "  target: tumbleweed (default), testing (Debian_Testing), sid (Debian_Unstable)"
  exit 2
fi
pkg="$1"; tgt="${2:-tumbleweed}"
case "$tgt" in
  Tumbleweed|openSUSE_Tumbleweed) tgt=tumbleweed ;;
  Debian_Testing) tgt=testing ;;
  Debian_Unstable) tgt=sid ;;
esac
case "$tgt" in
  tumbleweed) img=registry.opensuse.org/opensuse/tumbleweed:latest; setup='
    zypper --non-interactive --gpg-auto-import-keys addrepo --refresh https://download.opensuse.org/repositories/home:ackerman/openSUSE_Tumbleweed/ nexus >/tmp/r.log 2>&1 || { echo SETUP_REPO_FAIL; tail -3 /tmp/r.log; exit 2; }
    zypper --non-interactive --gpg-auto-import-keys addrepo --refresh https://download.opensuse.org/tumbleweed/repo/oss/ oss >/tmp/r.log 2>&1 || { echo SETUP_DISTRO_REPO_FAIL; tail -3 /tmp/r.log; exit 2; }
    zypper --non-interactive --gpg-auto-import-keys refresh >/tmp/r.log 2>&1 || { echo SETUP_REFRESH_FAIL; tail -3 /tmp/r.log; exit 2; }
    zypper --non-interactive install -y findutils >/tmp/r.log 2>&1 || { echo SETUP_FINDUTILS_FAIL; tail -3 /tmp/r.log; exit 2; }
    zypper --non-interactive install --no-recommends '"$pkg"' >/tmp/i.log 2>&1 || { echo SETUP_INSTALL_FAIL; tail -5 /tmp/i.log; exit 2; }' ;;
  testing|sid) img="debian:$tgt"; repo="Debian_Testing"; [ "$tgt" = sid ] && repo="Debian_Unstable"
    deb="${pkg}"
    if [ -f "$pkg/$pkg.dsc" ]; then
      deb=$(awk '/^Binary:/{print $2; exit}' "$pkg/$pkg.dsc")
    fi
    setup='
    apt-get update -qq >/tmp/r.log 2>&1 || { echo SETUP_INDEX_FAIL; tail -3 /tmp/r.log; exit 2; }
    install -d -m 0755 /etc/apt/keyrings
    curl -fsSL https://download.opensuse.org/repositories/home:ackerman/'"$repo"'/Release.key | gpg --dearmor -o /etc/apt/keyrings/obs-nexus.gpg >/tmp/r.log 2>&1 || { echo SETUP_KEY_FAIL; tail -3 /tmp/r.log; exit 2; }
    echo "deb [signed-by=/etc/apt/keyrings/obs-nexus.gpg] https://download.opensuse.org/repositories/home:ackerman/'"$repo"'/ /" > /etc/apt/sources.list.d/obs-nexus.list
    apt-get update -qq >/tmp/r.log 2>&1 || { echo SETUP_INDEX_FAIL; tail -3 /tmp/r.log; exit 2; }
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends '"$deb"' >/tmp/i.log 2>&1 || { echo SETUP_INSTALL_FAIL; tail -5 /tmp/i.log; exit 2; }' ;;
  *) echo "unknown target $tgt" >&2; exit 2 ;;
esac
timeout "${TMO:-900}" docker run --rm "$img" bash -lc '
  set -u
  '"$setup"'
  bad=0; found=0
  PKGFILES=$(rpm -ql "'"$pkg"'" 2>/dev/null || dpkg -L "'"$pkg"'" 2>/dev/null)
  for f in $(printf '%s\n' "$PKGFILES" | grep -E '\.desktop$' | head -40); do
    found=$((found+1))
    icon=$(grep -m1 "^Icon=" "$f" | cut -d= -f2)
    exec=$(grep -m1 "^Exec=" "$f" | cut -d= -f2 | cut -d" " -f1)
    case "$f" in
      /usr/share/applications/*)
        if [ -z "$icon" ]; then echo "ICON_UNSET $f"; bad=$((bad+1))
        elif ! find /usr/share/icons /usr/share/pixmaps /opt -iname "$icon.*" 2>/dev/null | grep -q .; then echo "ICON_MISSING $f $icon"; bad=$((bad+1)); fi ;;
    esac
    if [ -n "$exec" ]; then
      command -v "$exec" >/dev/null 2>&1 || find /opt -name "$exec" -type f 2>/dev/null | grep -q . || { echo "EXEC_MISSING $f $exec"; bad=$((bad+1)); }
    fi
  done
  if [ "$found" -eq 0 ]; then
    echo "desktop_files=0 NO_DESKTOP_ENTRY - installed payload ships no .desktop, not a pass"
    exit 3
  fi
  echo "desktop_files=$found bad=$bad"
  [ "$bad" -eq 0 ]
'
rc=$?
echo "desktop-audit: $pkg/$tgt rc=$rc"
exit "$rc"
