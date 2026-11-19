#!/usr/bin/env bash
# Install-test the published packages on all three OBS targets.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
LIST="${1:-tools/probes.txt}"
JOBS="${2:-4}"
[ -f "$LIST" ] || { echo "usage: $0 <listfile> [jobs]" >&2; exit 2; }
OUTDIR="${TD_OUTDIR:-/tmp/opencode/install-sweep}"
mkdir -p "$OUTDIR"
OUT="$OUTDIR/rows.txt"
: > "$OUT"

one() {
  local row="$1" pkg dnf_name deb_name smoke dsc
  IFS='|' read -r pkg dnf_name deb_name smoke <<< "$row"
  [ -n "$pkg" ] || return 0
  [ -n "$dnf_name" ] || dnf_name="$pkg"
  dsc=$(ls "$pkg"/*.dsc 2>/dev/null | head -1)
  if [ -z "$deb_name" ] && [ -n "$dsc" ]; then
    deb_name=$(awk '/^Binary:/{print $2; exit}' "$dsc")
  fi
  [ -n "$deb_name" ] || deb_name="$pkg"
  local tw='registry.opensuse.org/opensuse/tumbleweed:latest'
  local debt='debian:testing' debs='debian:sid'
  local tw_out deb_out
  tw_out=$(docker run --rm "$tw" bash -lc '
    set -u
    zypper --non-interactive --gpg-auto-import-keys addrepo --refresh https://download.opensuse.org/repositories/home:ackerman/openSUSE_Tumbleweed/ nexus >/dev/null 2>&1
    zypper --non-interactive --gpg-auto-import-keys refresh >/dev/null 2>&1
    zypper --non-interactive install --no-recommends "'"$dnf_name"'" >/tmp/i.log 2>&1 || { echo INSTALL_FAIL; grep -E "Problem|nothing provides|not found" /tmp/i.log | head -4; exit 1; }
    echo INSTALL_OK
    rpm -V "'"$dnf_name"'" >/tmp/v.log 2>&1 || { echo RPM_V_FAIL; head -4 /tmp/v.log; }
    markers=$(find /opt /usr/share /usr/lib -maxdepth 6 \( -name app-update.yml -o -name package-type \) 2>/dev/null | wc -l)
    echo "markers=$markers"
    ship=" "
    for lib in $(rpm -ql "'"$dnf_name"'" 2>/dev/null | grep -E "\.so"); do ship="$ship $(basename $lib) "; done
    miss=0
    for f in $(rpm -ql "'"$dnf_name"'" 2>/dev/null | grep -E "^/usr/bin/|^/opt/" | head -40); do
      [ -f "$f" ] && [ -x "$f" ] && head -c4 "$f" 2>/dev/null | grep -q ELF || continue
      case "$f" in
        *.so|*.so.[0-9]*) fatal=0 ;;
        *) fatal=1 ;;
      esac
      for need in $(ldd "$f" 2>/dev/null | grep "not found" | cut -d" " -f1); do
        case "$ship" in *" $need "*) continue ;; esac
        if [ "$fatal" = 1 ]; then miss=$((miss + 1)); echo "REAL_MISS $need <- $f"; else echo "OPT_MISS $need <- $f"; fi
      done
    done
    echo "ldd_missing=$miss"
    if [ -n "'"$smoke"'" ]; then
      timeout 30 sh -c "'"$smoke"'" >/tmp/s.log 2>&1; echo "smoke_rc=$?"; head -2 /tmp/s.log
    fi
  ' 2>&1) || true
  local tw_verdict=FAIL
  printf '%s\n' "$tw_out" > "$OUTDIR/$pkg-tumbleweed.log"
  printf '%s\n' "$tw_out" | grep -q INSTALL_OK && printf '%s\n' "$tw_out" | grep -q 'markers=0' && printf '%s\n' "$tw_out" | grep -q 'ldd_missing=0' && ! printf '%s\n' "$tw_out" | grep -q RPM_V_FAIL && { [ -z "$smoke" ] || printf '%s\n' "$tw_out" | grep -q 'smoke_rc=0'; } && tw_verdict=PASS
  if [ -z "$dsc" ]; then
    printf '| %s | tumbleweed | %s |\n' "$pkg" "$tw_verdict" >> "$OUT"
    echo "=== $pkg tumbleweed=$tw_verdict deb=n/a-no-dsc"
    return 0
  fi
  for tgt_name in testing sid; do
    local img="$debt"; [ "$tgt_name" = sid ] && img="$debs"
    local repo="Debian_Testing"; [ "$tgt_name" = sid ] && repo="Debian_Unstable"
    deb_out=$(docker run --rm "$img" bash -lc '
      set -u
      apt-get update -qq >/dev/null 2>&1
      apt-get install -y -qq ca-certificates curl gnupg >/dev/null 2>&1
      install -d -m 0755 /etc/apt/keyrings
      curl -fsSL https://download.opensuse.org/repositories/home:ackerman/'"$repo"'/Release.key | gpg --dearmor -o /etc/apt/keyrings/obs-nexus.gpg >/dev/null 2>&1
      echo "deb [signed-by=/etc/apt/keyrings/obs-nexus.gpg] https://download.opensuse.org/repositories/home:ackerman/'"$repo"'/ /" > /etc/apt/sources.list.d/obs-nexus.list
      apt-get update -qq >/dev/null 2>&1
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "'"$deb_name"'" >/tmp/i.log 2>&1 || { echo INSTALL_FAIL; grep -E "E:|unable to locate" /tmp/i.log | head -4; exit 1; }
      echo INSTALL_OK
      dpkg -V "'"$deb_name"'" >/tmp/v.log 2>&1 || { echo DPKG_V_FAIL; head -4 /tmp/v.log; }
      markers=$(find /opt /usr/share /usr/lib -maxdepth 6 \( -name app-update.yml -o -name package-type \) 2>/dev/null | wc -l)
      echo "markers=$markers"
      ship=" "
      for lib in $(dpkg -L "'"$deb_name"'" 2>/dev/null | grep -E "\.so"); do ship="$ship $(basename $lib) "; done
      miss=0
      for f in $(dpkg -L "'"$deb_name"'" 2>/dev/null | grep -E "^/usr/bin/|^/opt/" | head -40); do
        [ -f "$f" ] && [ -x "$f" ] && head -c4 "$f" 2>/dev/null | grep -q ELF || continue
        case "$f" in
          *.so|*.so.[0-9]*) fatal=0 ;;
          *) fatal=1 ;;
        esac
        for need in $(ldd "$f" 2>/dev/null | grep "not found" | cut -d" " -f1); do
          case "$ship" in *" $need "*) continue ;; esac
          if [ "$fatal" = 1 ]; then miss=$((miss + 1)); echo "REAL_MISS $need <- $f"; else echo "OPT_MISS $need <- $f"; fi
        done
      done
      echo "ldd_missing=$miss"
      if [ -n "'"$smoke"'" ]; then
        timeout 30 sh -c "'"$smoke"'" >/tmp/s.log 2>&1; echo "smoke_rc=$?"; head -2 /tmp/s.log
      fi
    ' 2>&1) || true
    local dv=FAIL
    printf '%s\n' "$deb_out" > "$OUTDIR/$pkg-$tgt_name.log"
    printf '%s\n' "$deb_out" | grep -q INSTALL_OK && printf '%s\n' "$deb_out" | grep -q 'markers=0' && printf '%s\n' "$deb_out" | grep -q 'ldd_missing=0' && ! printf '%s\n' "$deb_out" | grep -q DPKG_V_FAIL && { [ -z "$smoke" ] || printf '%s\n' "$deb_out" | grep -q 'smoke_rc=0'; } && dv=PASS
    printf '| %s | %s | %s |\n' "$pkg" "$tgt_name" "$dv" >> "$OUT"
  done
  printf '| %s | tumbleweed | %s |\n' "$pkg" "$tw_verdict" >> "$OUT"
  echo "=== $pkg tumbleweed=$tw_verdict"
}

export -f one
export OUT
n=0
while IFS= read -r row; do
  [ -z "$row" ] && continue
  one "$row" &
  n=$((n + 1))
  if [ $((n % JOBS)) -eq 0 ]; then wait; fi
done < "$LIST"
wait
echo "rows: $OUT"
cat "$OUT"
