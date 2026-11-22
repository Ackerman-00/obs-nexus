#!/usr/bin/env bash
# PikaOS compatibility: install our published DEBs on the PikaOS rebuilt stack.
set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 2
LIST="tools/probes.txt"
REPO="${PIKA_OBS_REPO:-Debian_Unstable}"
for arg in "$@"; do
  case "$arg" in
    --repo=*) REPO="${arg#--repo=}" ;;
    -h|--help) echo "usage: $0 [listfile] [--repo=Debian_Unstable|Debian_Testing]"; exit 0 ;;
    *) LIST="$arg" ;;
  esac
done
case "$REPO" in Debian_Unstable|Debian_Testing) ;; *) echo "unknown OBS repo $REPO" >&2; exit 2 ;; esac
[ -f "$LIST" ] || { echo "usage: $0 [listfile] [--repo=...]" >&2; exit 2; }
OUTDIR="${PIKA_OUTDIR:-/tmp/opencode/pikaos}"
mkdir -p "$OUTDIR"
OUT="$OUTDIR/rows.txt"
: > "$OUT"

# ppa.pika-os.com answers a Bunny Shield JS challenge (HTTP 403) to non-browser
# clients; repo.pika-os.com serves the same flat suites and needs ca-certificates.
probe() {
  PIKA_DEB="$1" PIKA_REPO="$2" timeout "${PIKA_TIMEOUT:-1500}" \
    docker run --rm -i -e PIKA_DEB -e PIKA_REPO debian:sid bash -s <<'EOS' 2>&1
set -u
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::http::Timeout=40 update -qq >/dev/null 2>&1 || { echo "HARNESS_BASE_INDEX_FAIL"; exit 2; }
apt-get install -y -qq ca-certificates curl gnupg >/dev/null 2>&1 || { echo "HARNESS_BASE_TOOLS_FAIL"; exit 2; }
printf 'deb [trusted=yes] https://repo.pika-os.com pika/nest ./\ndeb [trusted=yes] https://repo.pika-os.com pika/cockatiel ./\n' > /etc/apt/sources.list.d/pika.list
apt-get -o Acquire::http::Timeout=180 update -qq >/tmp/u.log 2>&1 || { echo "HARNESS_PIKA_INDEX_FAIL"; tail -2 /tmp/u.log; exit 2; }
apt-cache policy 2>/dev/null | grep -q 'repo.pika-os.com' || { echo "HARNESS_PIKA_INDEX_EMPTY"; exit 2; }
apt-get install -y -qq --allow-downgrades mesa-vulkan-drivers libavcodec61 libavformat61 >/tmp/p.log 2>&1 \
  || { echo "HARNESS_PIKA_STACK_FAIL"; tail -3 /tmp/p.log; exit 2; }
install -d -m 0755 /etc/apt/keyrings
curl -fsSL "https://download.opensuse.org/repositories/home:ackerman/$PIKA_REPO/Release.key" \
  | gpg --dearmor -o /etc/apt/keyrings/obs-nexus.gpg >/tmp/k.log 2>&1 || { echo "HARNESS_OBS_KEY_FAIL"; tail -2 /tmp/k.log; exit 2; }
echo "deb [signed-by=/etc/apt/keyrings/obs-nexus.gpg] https://download.opensuse.org/repositories/home:ackerman/$PIKA_REPO/ /" > /etc/apt/sources.list.d/obs-nexus.list
apt-get -o Acquire::http::Timeout=60 update -qq >/tmp/u.log 2>&1 || { echo "HARNESS_OBS_INDEX_FAIL"; tail -2 /tmp/u.log; exit 2; }
apt-cache policy "$PIKA_DEB" 2>/dev/null | grep -qE 'Candidate: [0-9]' || { echo "INDEX_MISSING $PIKA_DEB"; exit 3; }
apt-get install -y -qq --no-install-recommends "$PIKA_DEB" >/tmp/i.log 2>&1 || { echo "INSTALL_FAIL"; grep -m3 -E 'E:|Depends|nothing' /tmp/i.log; exit 1; }
down=$(grep -ci downgrad /tmp/i.log || true)
dpkg -V "$PIKA_DEB" >/tmp/v.log 2>&1 || { echo "DPKG_V_FAIL"; head -3 /tmp/v.log; exit 1; }
miss=0
for f in $(dpkg -L "$PIKA_DEB" 2>/dev/null | grep -E '^/opt/|^/usr/bin/|^/usr/lib/' | head -40); do
  [ -f "$f" ] || continue
  [ "$(head -c4 "$f" | od -An -c | tr -d ' \n')" = "177ELF" ] || continue
  m=$(ldd "$f" 2>/dev/null | grep -c 'not found' || true)
  miss=$((miss + m))
done
held=$(dpkg -l | grep -cE '^(hi|hB)' || true)
sandbox=$(find /opt -maxdepth 4 -name chrome-sandbox -printf '%M' 2>/dev/null | head -1)
echo "INSTALL_OK downgrades=$down dpkg_v=clean ldd_missing=$miss held_broken=$held sandbox=${sandbox:-none}"
EOS
}

run_one() {
  local pkg="$1" repo="$2" out="$3" deb raw verdict detail
  deb="$pkg"
  [ -f "$pkg/$pkg.dsc" ] && deb=$(awk '/^Binary:/{print $2; exit}' "$pkg/$pkg.dsc")
  raw=$(probe "$deb" "$repo")
  if grep -q '^INSTALL_OK' <<< "$raw"; then
    verdict=PASS; detail=$(grep '^INSTALL_OK' <<< "$raw" | sed 's/^INSTALL_OK //')
  elif grep -qE '^HARNESS_|^INDEX_MISSING' <<< "$raw"; then
    verdict=EXTERNAL; detail=$(grep -m1 -E '^HARNESS_|^INDEX_MISSING' <<< "$raw")
  else
    verdict=FAIL; detail=$(grep -m1 -E '^INSTALL_FAIL|^DPKG_V_FAIL' <<< "$raw")
  fi
  printf '| %s | pikaos (%s) | %s | %s |\n' "$pkg" "$repo" "$verdict" "$detail" >> "$out"
}
export -f probe run_one

names=$(grep -vE '^[[:space:]]*(#|$)' "$LIST" | cut -d'|' -f1)
printf '%s\n' "$names" | xargs -P "${PIKA_JOBS:-4}" -I{} bash -c 'run_one "$@"' _ {} "$REPO" "$OUT"
sort -t'|' -k2,2 "$OUT" -o "$OUT"
pass=$(grep -c '| PASS |' "$OUT" || true)
fail=$(grep -c '| FAIL |' "$OUT" || true)
ext=$(grep -c '| EXTERNAL |' "$OUT" || true)
echo "pikaos-compat: $pass PASS / $fail FAIL / $ext EXTERNAL of $(wc -l < "$OUT") packages (repo $REPO)"
[ "$fail" -eq 0 ]
