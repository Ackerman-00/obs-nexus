#!/usr/bin/env bash
# Resolve every shipped .desktop entry in a published package.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
[ $# -ge 1 ] || { echo "usage: $0 <pkg> [tumbleweed|testing|sid]" >&2; exit 2; }
pkg="$1"; tgt="${2:-tumbleweed}"
case "$tgt" in
  tumbleweed) img=registry.opensuse.org/opensuse/tumbleweed:latest; setup='
    zypper --non-interactive --gpg-auto-import-keys addrepo --refresh https://download.opensuse.org/repositories/home:ackerman/openSUSE_Tumbleweed/ nexus >/dev/null 2>&1
    zypper --non-interactive --gpg-auto-import-keys refresh >/dev/null 2>&1
    zypper --non-interactive install --no-recommends '"$pkg"' >/dev/null 2>&1' ;;
  testing|sid) img="debian:$tgt"; repo="Debian_Testing"; [ "$tgt" = sid ] && repo="Debian_Unstable"; setup='
    apt-get update -qq >/dev/null 2>&1
    install -d -m 0755 /etc/apt/keyrings
    curl -fsSL https://download.opensuse.org/repositories/home:ackerman/'"$repo"'/Release.key | gpg --dearmor -o /etc/apt/keyrings/obs-nexus.gpg >/dev/null 2>&1
    echo "deb [signed-by=/etc/apt/keyrings/obs-nexus.gpg] https://download.opensuse.org/repositories/home:ackerman/'"$repo"'/ /" > /etc/apt/sources.list.d/obs-nexus.list
    apt-get update -qq >/dev/null 2>&1
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends '"$pkg"' >/dev/null 2>&1' ;;
  *) echo "unknown target $tgt" >&2; exit 2 ;;
esac
docker run --rm "$img" bash -lc '
  set -u
  '"$setup"'
  bad=0; found=0
  for f in $(find /usr/share/applications /usr/share/xsessions /usr/share/wayland-sessions /opt -name "*.desktop" 2>/dev/null | head -40); do
    found=$((found+1))
    icon=$(grep -m1 "^Icon=" "$f" | cut -d= -f2)
    exec=$(grep -m1 "^Exec=" "$f" | cut -d= -f2 | awk "{print \\$1}")
    case "$f" in
      /usr/share/applications/*)
        if [ -n "$icon" ] && ! find /usr/share/icons /usr/share/pixmaps /opt -iname "$icon.*" 2>/dev/null | grep -q .; then echo "ICON_MISSING $f $icon"; bad=$((bad+1)); fi ;;
    esac
    if [ -n "$exec" ]; then
      command -v "$exec" >/dev/null 2>&1 || find /opt -name "$exec" -type f 2>/dev/null | grep -q . || { echo "EXEC_MISSING $f $exec"; bad=$((bad+1)); }
    fi
  done
  echo "desktop_files=$found bad=$bad"
  [ "$bad" -eq 0 ]
'
echo "desktop-audit: $pkg/$tgt rc=$?"
