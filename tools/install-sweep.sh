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
TMO="${TD_TIMEOUT:-900}"
: > "$OUT"

tw_probe() {
  local img="$1" name="$2" smoke="$3"
  timeout "$TMO" docker run --rm "$img" bash -lc '
    set -u
    ok=0
    for attempt in 1 2 3; do
      zypper --non-interactive --gpg-auto-import-keys addrepo --refresh https://download.opensuse.org/repositories/home:ackerman/openSUSE_Tumbleweed/ nexus >/tmp/r.log 2>&1 && ok=1 && break
      zypper --non-interactive removerepo nexus >/dev/null 2>&1
      sleep 3
    done
    [ "$ok" = 1 ] || { echo HARNESS_REPO_ADD_FAIL; tail -3 /tmp/r.log; exit 2; }
    ok=0
    for attempt in 1 2 3; do
      zypper --non-interactive --gpg-auto-import-keys refresh >/tmp/r.log 2>&1 && ok=1 && break
      sleep 3
    done
    [ "$ok" = 1 ] || { echo HARNESS_REPO_REFRESH_FAIL; tail -3 /tmp/r.log; exit 2; }
    zypper --non-interactive install --no-recommends "'"$name"'" >/tmp/i.log 2>&1 || { echo INSTALL_FAIL; grep -E "Problem|nothing provides|not found|not available" /tmp/i.log | head -4; exit 1; }
    echo INSTALL_OK
    rpm -V "'"$name"'" >/tmp/v.log 2>&1 || { echo RPM_V_FAIL; head -4 /tmp/v.log; }
    markers=$(find /opt /usr/share /usr/lib -maxdepth 6 \( -name app-update.yml -o -name package-type \) 2>/dev/null | wc -l)
    echo "markers=$markers"
    ship=" "
    for lib in $(rpm -ql "'"$name"'" 2>/dev/null | grep -E "\.so"); do ship="$ship $(basename $lib) "; done
    miss=0
    for f in $(rpm -ql "'"$name"'" 2>/dev/null | grep -E "^/usr/bin/|^/opt/" | head -40); do
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
  ' 2>&1
}

deb_probe() {
  local img="$1" repo="$2" name="$3" smoke="$4"
  timeout "$TMO" docker run --rm "$img" bash -lc '
    set -u
    ok=0
    for attempt in 1 2 3; do
      apt-get -o Acquire::http::Timeout=25 -o Acquire::https::Timeout=25 -o Acquire::Retries=2 update -qq >/tmp/u.log 2>&1 && ok=1 && break
      sleep 3
    done
    [ "$ok" = 1 ] || { echo HARNESS_BASE_INDEX_FAIL; tail -3 /tmp/u.log; exit 2; }
    apt-get -o Acquire::http::Timeout=25 -o Acquire::https::Timeout=25 -o Acquire::Retries=2 install -y -qq ca-certificates curl gnupg >/tmp/u.log 2>&1 || { echo HARNESS_BASE_TOOLS_FAIL; tail -3 /tmp/u.log; exit 2; }
    install -d -m 0755 /etc/apt/keyrings
    curl -fsSL --max-time 40 --retry 2 https://download.opensuse.org/repositories/home:ackerman/'"$repo"'/Release.key -o /tmp/Release.key || { echo HARNESS_KEY_FETCH_FAIL; exit 2; }
    gpg --dearmor -o /etc/apt/keyrings/obs-nexus.gpg /tmp/Release.key >/dev/null 2>&1 || { echo HARNESS_KEY_DECODE_FAIL; exit 2; }
    echo "deb [signed-by=/etc/apt/keyrings/obs-nexus.gpg] https://download.opensuse.org/repositories/home:ackerman/'"$repo"'/ /" > /etc/apt/sources.list.d/obs-nexus.list
    ok=0
    for attempt in 1 2 3; do
      apt-get -o Acquire::http::Timeout=25 -o Acquire::https::Timeout=25 -o Acquire::Retries=2 update -qq >/tmp/u.log 2>&1 && ok=1 && break
      sleep 3
    done
    [ "$ok" = 1 ] || { echo HARNESS_OBS_INDEX_FAIL; tail -3 /tmp/u.log; exit 2; }
    apt-cache policy "'"$name"'" 2>/dev/null | grep -qE "Candidate: [^ ]" || { echo INDEX_MISSING "'"$name"'"; apt-cache policy "'"$name"'" 2>&1 | head -2; exit 3; }
    DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::http::Timeout=25 -o Acquire::https::Timeout=25 -o Acquire::Retries=2 install -y --no-install-recommends "'"$name"'" >/tmp/i.log 2>&1 || { echo INSTALL_FAIL; grep -E "E:|unable to locate" /tmp/i.log | head -4; exit 1; }
    echo INSTALL_OK
    dpkg -V "'"$name"'" >/tmp/v.log 2>&1 || { echo DPKG_V_FAIL; head -4 /tmp/v.log; }
    markers=$(find /opt /usr/share /usr/lib -maxdepth 6 \( -name app-update.yml -o -name package-type \) 2>/dev/null | wc -l)
    echo "markers=$markers"
    ship=" "
    for lib in $(dpkg -L "'"$name"'" 2>/dev/null | grep -E "\.so"); do ship="$ship $(basename $lib) "; done
    miss=0
    for f in $(dpkg -L "'"$name"'" 2>/dev/null | grep -E "^/usr/bin/|^/opt/" | head -40); do
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
  ' 2>&1
}

# an index/CDN flake is a harness verdict, never a package verdict
verdict_of() {
  local out="$1" mark="$2" smoke="$3"
  if printf '%s\n' "$out" | grep -q '^INDEX_MISSING'; then echo FAIL; return; fi
  if printf '%s\n' "$out" | grep -q '^HARNESS_'; then echo HARNESS; return; fi
  if ! printf '%s\n' "$out" | grep -qE 'INSTALL_OK|INSTALL_FAIL'; then echo HARNESS; return; fi
  if printf '%s\n' "$out" | grep -qiE 'unable to locate|unable to fetch|could not connect|connection timed out|failed to fetch|failed to retrieve|download failed|temporary failure|network is unreachable|curl: \(|timed out'; then echo HARNESS; return; fi
  if printf '%s\n' "$out" | grep -q INSTALL_OK \
     && printf '%s\n' "$out" | grep -q 'markers=0' \
     && printf '%s\n' "$out" | grep -q 'ldd_missing=0' \
     && ! printf '%s\n' "$out" | grep -q "$mark" \
     && { [ -z "$smoke" ] || printf '%s\n' "$out" | grep -q 'smoke_rc=0'; }; then echo PASS; return; fi
  echo FAIL
}

flaked() {
  printf '%s\n' "$1" | grep -q '^HARNESS_' && return 0
  printf '%s\n' "$1" | grep -qiE 'unable to locate|unable to fetch|could not connect|connection timed out|failed to fetch|failed to retrieve|download failed|temporary failure|network is unreachable|curl: \(|timed out' && return 0
  return 1
}

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
  local tw_out deb_out try
  tw_out=$(tw_probe "$tw" "$dnf_name" "$smoke")
  for try in 2 3; do
    flaked "$tw_out" || break
    sleep $((try * 5))
    tw_out=$(tw_probe "$tw" "$dnf_name" "$smoke")
  done
  local tw_verdict
  tw_verdict=$(verdict_of "$tw_out" RPM_V_FAIL "$smoke")
  printf '%s\n' "$tw_out" > "$OUTDIR/$pkg-tumbleweed.log"
  if [ -z "$dsc" ]; then
    printf '| %s | tumbleweed | %s |\n' "$pkg" "$tw_verdict" >> "$OUT"
    echo "=== $pkg tumbleweed=$tw_verdict deb=n/a-no-dsc"
    return 0
  fi
  for tgt_name in testing sid; do
    local img="$debt"; [ "$tgt_name" = sid ] && img="$debs"
    local repo="Debian_Testing"; [ "$tgt_name" = sid ] && repo="Debian_Unstable"
    deb_out=$(deb_probe "$img" "$repo" "$deb_name" "$smoke")
    for try in 2 3; do
      flaked "$deb_out" || break
      sleep $((try * 5))
      deb_out=$(deb_probe "$img" "$repo" "$deb_name" "$smoke")
    done
    local dv
    dv=$(verdict_of "$deb_out" DPKG_V_FAIL "$smoke")
    printf '%s\n' "$deb_out" > "$OUTDIR/$pkg-$tgt_name.log"
    printf '| %s | %s | %s |\n' "$pkg" "$tgt_name" "$dv" >> "$OUT"
  done
  printf '| %s | tumbleweed | %s |\n' "$pkg" "$tw_verdict" >> "$OUT"
  echo "=== $pkg tumbleweed=$tw_verdict"
}

export -f one tw_probe deb_probe verdict_of flaked
export OUT OUTDIR TMO
n=0
while IFS= read -r row; do
  [ -z "$row" ] && continue
  case "$row" in \#*) continue ;; esac
  one "$row" &
  n=$((n + 1))
  if [ $((n % JOBS)) -eq 0 ]; then wait; fi
done < "$LIST"
wait
echo "rows: $OUT"
cat "$OUT"
