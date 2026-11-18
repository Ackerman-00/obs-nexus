#!/usr/bin/env bash
# Install-test the published packages on all three OBS targets.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
LIST="${1:-tools/probes.txt}"
JOBS="${2:-4}"
[ -f "$LIST" ] || { echo "usage: $0 <listfile> [jobs]" >&2; exit 2; }
mkdir -p /tmp/opencode/install-sweep
OUT="${TD_OUTDIR:-/tmp/opencode/install-sweep}/rows.txt"
: > "$OUT"

one() {
  local row="$1" pkg dnf_name smoke
  IFS='|' read -r pkg dnf_name smoke <<< "$row"
  [ -n "$pkg" ] || return 0
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
    miss=0
    for f in $(rpm -ql "'"$dnf_name"'" 2>/dev/null | grep -E "^/usr/bin/|^/opt/" | head -40); do
      [ -f "$f" ] && [ -x "$f" ] && head -c4 "$f" 2>/dev/null | grep -q ELF || continue
      n=$(ldd "$f" 2>/dev/null | grep -c "not found"); miss=$((miss + n))
    done
    echo "ldd_missing=$miss"
  ' 2>&1) || true
  local tw_verdict=FAIL
  printf '%s\n' "$tw_out" | grep -q INSTALL_OK && printf '%s\n' "$tw_out" | grep -q 'markers=0' && printf '%s\n' "$tw_out" | grep -q 'ldd_missing=0' && ! printf '%s\n' "$tw_out" | grep -q RPM_V_FAIL && tw_verdict=PASS
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
      DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "'"$dnf_name"'" >/tmp/i.log 2>&1 || { echo INSTALL_FAIL; grep -E "E:|unable to locate" /tmp/i.log | head -4; exit 1; }
      echo INSTALL_OK
      dpkg -V "'"$dnf_name"'" >/tmp/v.log 2>&1 || { echo DPKG_V_FAIL; head -4 /tmp/v.log; }
      markers=$(find /opt /usr/share /usr/lib -maxdepth 6 \( -name app-update.yml -o -name package-type \) 2>/dev/null | wc -l)
      echo "markers=$markers"
      miss=0
      for f in $(dpkg -L "'"$dnf_name"'" 2>/dev/null | grep -E "^/usr/bin/|^/opt/" | head -40); do
        [ -f "$f" ] && [ -x "$f" ] && head -c4 "$f" 2>/dev/null | grep -q ELF || continue
        n=$(ldd "$f" 2>/dev/null | grep -c "not found"); miss=$((miss + n))
      done
      echo "ldd_missing=$miss"
    ' 2>&1) || true
    local dv=FAIL
    printf '%s\n' "$deb_out" | grep -q INSTALL_OK && printf '%s\n' "$deb_out" | grep -q 'markers=0' && printf '%s\n' "$deb_out" | grep -q 'ldd_missing=0' && ! printf '%s\n' "$deb_out" | grep -q DPKG_V_FAIL && dv=PASS
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
