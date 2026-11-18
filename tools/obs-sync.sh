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
  # debtransform orig tarball: gitignored, must exist on OBS for the DEB targets
  for dsc in "$pkg"/*.dsc; do
    [ -f "$dsc" ] || continue
    tar=$(grep -E '^Debtransform-Tar:[[:space:]]*' "$dsc" | awk '{print $2}')
    [ -n "$tar" ] || continue
    if [ -f "$pkg/$tar" ]; then
      case " $remote " in *" $tar "*) ;; *)
        code=$(curl -s -o /dev/null -w '%{http_code}' -u "$OBS_USER:$OBS_PASS" -T "$pkg/$tar" "$API/$pkg/$tar")
        echo "  PUT orig $tar -> HTTP $code"
        [ "$code" = "200" ] || fail=1
      ;; esac
    fi
  done
  # superseded source artifacts: unreferenced remote name whose stem a kept artifact owns
  export REMOTE_ARTIFACTS="$remote"
  verdicts=$(python3 - "$pkg" <<'PY'
import glob, os, re, sys
pkg = sys.argv[1]
ART = ('.tar.gz', '.tar.xz', '.tar.bz2', '.tar.zst', '.tgz', '.appimage', '.deb', '.rpm', '.zip')
keep = set()
for f in glob.glob(pkg + '/*'):
    if os.path.isfile(f) and f.lower().endswith(ART):
        keep.add(os.path.basename(f))
for d in glob.glob(pkg + '/*.dsc'):
    m = re.search(r'^Debtransform-Tar:\s*(\S+)', open(d, errors='replace').read(), re.M)
    if m:
        keep.add(m.group(1))
for s in glob.glob(pkg + '/*.spec'):
    t = open(s, errors='replace').read()
    mac = {}
    for m in re.finditer(r'^%(?:global|define)\s+(\w+)\s+(\S+)', t, re.M):
        mac.setdefault(m.group(1), m.group(2))
    for key, pat in (('name', r'^Name:\s*(\S+)'), ('version', r'^Version:\s*(\S+)')):
        m = re.search(pat, t, re.M)
        if m:
            mac.setdefault(key, m.group(1))
    for m in re.finditer(r'^Source\d+:\s*(\S+)', t, re.M):
        cur = os.path.basename(m.group(1).split('?')[0])
        for _ in range(4):
            new = re.sub(r'%\{(\w+)\}', lambda mm: mac.get(mm.group(1), mm.group(0)), cur)
            if new == cur:
                break
            cur = new
        if '%' not in cur and cur.lower().endswith(ART):
            keep.add(cur)
for sv in glob.glob(pkg + '/_service'):
    for m in re.finditer(r'<param\s+name="filename">\s*([^<]+?)\s*</param>', open(sv).read()):
        keep.add(m.group(1))
def stem(n):
    for e in ART:
        if n.lower().endswith(e):
            n = n[:-len(e)]
            break
    n = re.sub(r'[0-9a-f]{7,40}', '', n, flags=re.I)
    n = re.sub(r'\d+(?:[._+~-][0-9A-Za-z]+)*', '', n)
    return re.sub(r'[-_.+]+', '-', n).strip('-').lower()
for f in os.environ.get('REMOTE_ARTIFACTS', '').split():
    if f in keep or os.path.isfile(pkg + '/' + f):
        continue
    twin = next((k for k in sorted(keep) if stem(k) == stem(f)), None)
    print(('DELETE ' + f + ' superseded-by-' + twin) if twin else ('KEEP ' + f))
PY
)
  while read -r action name reason; do
    case "$action" in
      DELETE)
        code=$(curl -s -o /dev/null -w '%{http_code}' -u "$OBS_USER:$OBS_PASS" -X DELETE "$API/$pkg/$name")
        echo "  DELETE superseded $name ($reason) -> HTTP $code"
        [ "$code" = "200" ] || fail=1
      ;;
      KEEP) echo "  keep remote artifact $name" ;;
    esac
  done <<< "$verdicts"
  for f in $remote; do
    [ -f "$pkg/$f" ] && continue
    case "$f" in
      *.spec|*.changes|*.dsc|debian.*|_service|*.rpmlintrc|*.desktop|*.patch|*.py) ;;
      *) continue ;;
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
