#!/bin/bash
# fleet-rotate.sh — FLEET BATTLE-TEST ROTATION helper (run every schedule):
# rebuild one slice of the fleet from the CURRENT spec in a fresh
# Tumbleweed container, install the result, rpm -V it, smoke-test the
# binary and ldd-scan it. OBS binaries are NOT enough: this proves the
# current git spec still builds+installs end to end on today's toolchain.
#
# Usage:  tools/fleet-rotate.sh "<pkg> <pkg> ..."   (slice for this run)
#    or:  tools/fleet-rotate.sh all                  (whole fleet; slow)
#
# Package names are always derived from */*.spec on disk (never hardcoded).
# Needs: OBS_USER/OBS_PASS env (source artifacts), docker, /tmp space.
# Exit: nonzero if ANY package in the slice fails (rc 21 deps, 22 build,
# 23 install; container/tooling errors bubble up). Output per package is a
# self-contained evidence block; keep it in the relay.
set -u
export OBS_USER OBS_PASS
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT" || exit 1
[ $# -ge 1 ] || { echo "usage: $0 \"<pkg> ...\" | all" >&2; exit 2; }
if [ "$1" = all ]; then
  PKGS=$(ls -d */ | sed 's#/##' | while read -r d; do [ -f "$d/$d.spec" ] && echo "$d"; done | tr '\n' ' ')
else
  PKGS="$1"
fi
IMG=registry.opensuse.org/opensuse/tumbleweed:latest
mkdir -p /tmp/rot/src /tmp/rot/out
fail=0
for pkg in $PKGS; do
  echo "=== ROTATE $pkg ==="
  [ -f "$pkg/$pkg.spec" ] || { echo "$pkg: no spec in repo"; fail=1; continue; }
  sd=/tmp/rot/src/$pkg
  rm -rf "$sd"; mkdir -p "$sd"
  # spec from git tree (authoritative), source artifacts from OBS
  cp "$pkg/$pkg.spec" "$sd/"
  files=$(curl -s -u "$OBS_USER:$OBS_PASS" "https://api.opensuse.org/source/home:ackerman/$pkg" | grep -oE 'name="[^"]+"' | sed 's/name="//;s/"//' | grep -v '^_')
  for f in $files; do
    case "$f" in
      *.spec|*.changes|_service|update.sh|*.rpmlintrc|debian.*|*.dsc) ;;
      *) curl -s -u "$OBS_USER:$OBS_PASS" -o "$sd/$f" "https://api.opensuse.org/source/home:ackerman/$pkg/$f" && echo "  fetched $f" ;;
    esac
  done
  # download_files-service packages: remote Source URLs are not committed to
  # OBS - fetch them directly so %prep finds them in SOURCES.
  grep -hE "^Source[0-9]*:[[:space:]]+https?://" "$sd/$pkg.spec" | sed -E 's/^Source[0-9]*:[[:space:]]+//' | sort -u | while read -r url; do
    bn=$(basename "$url")
    [ -f "$sd/$bn" ] || { curl -fsSL --retry 3 -o "$sd/$bn" "$url" && echo "  fetched-url $bn"; }
  done
  docker run --rm -v "$sd:/src:ro" -v /tmp/rot/out:/out -e pkg="$pkg" "$IMG" bash -lc '
    set -u
    # repo-self-deps: some packages BuildRequire libs this project itself
    # ships (e.g. mangowm -> pkgconfig(scenefx-0.5), absent from TW). OBS
    # resolves those via project-internal deps; locally the same set comes
    # from the published nexus mirror - the exact repo a user adds per
    # README - so add it before resolving BuildRequires. Official TW repos
    # stay enabled and still provide everything else.
    zypper --non-interactive addrepo --refresh https://download.opensuse.org/repositories/home:/ackerman/openSUSE_Tumbleweed/ home_ackerman >/dev/null 2>&1
    zypper --non-interactive --gpg-auto-import-keys refresh >/dev/null 2>&1
    zypper --non-interactive --no-gpg-checks in -y rpm-build >/dev/null 2>&1
    mkdir -p /usr/src/packages/{SOURCES,SPECS,BUILD,BUILDROOT,RPMS,SRPMS}
    cp /src/*.spec /usr/src/packages/SPECS/ 2>/dev/null
    for f in /src/*; do case "$f" in *.spec) ;; *) cp "$f" /usr/src/packages/SOURCES/ ;; esac; done
    spec=/usr/src/packages/SPECS/'"$pkg"'.spec
    # macro-form Source URLs: expand via rpmspec and fetch whatever is not
    # already in SOURCES (the OBS download_files service does this at build
    # time; rpm _topdir on openSUSE is /usr/src/packages, NOT ~/rpmbuild).
    rpmspec --parse "$spec" 2>/dev/null | grep -E "^Source[0-9]*:[[:space:]]*https?://" | sed -E "s/^Source[0-9]*:[[:space:]]*//" | sort -u | while read -r url; do
      bn=$(basename "$url")
      [ -f /usr/src/packages/SOURCES/"$bn" ] || { curl -fsSL --retry 3 --connect-timeout 30 -o /usr/src/packages/SOURCES/"$bn" "$url" && echo "  url-fetched $bn"; } || echo "  url-fetch-failed $bn ($url)"
    done
    br=$(rpmspec -q --buildrequires "$spec" 2>/dev/null)
    echo "--- buildrequires: $(echo "$br" | wc -l) deps"
    if [ -n "$br" ]; then
      zypper --non-interactive --no-gpg-checks in -y --no-recommends $br >/tmp/br.log 2>&1 || { echo "--- DEPS-RESOLVE-FAIL"; tail -5 /tmp/br.log; exit 21; }
    fi
    rpmbuild -ba "$spec" >/tmp/build.log 2>&1 || { echo "--- BUILD-FAIL"; tail -25 /tmp/build.log; exit 22; }
    echo "--- BUILD OK"
    # glob ALL arch dirs: noarch packages (BuildArch: noarch) land in
    # RPMS/noarch/, and an empty $rpms made zypper print usage -> rc=23
    # (was misread as a package defect on bibata-cursor-theme/faugus).
    rpms=$(ls /usr/src/packages/RPMS/*/*.rpm 2>/dev/null)
    cp $rpms /out/ 2>/dev/null
    zypper --non-interactive --no-gpg-checks in -y --no-recommends $rpms >/tmp/inst.log 2>&1 || { echo "--- INSTALL-FAIL"; tail -8 /tmp/inst.log; exit 23; }
    echo "--- INSTALL OK"
    rpm -V '"$pkg"' && echo "--- RPM-V OK" || echo "--- RPM-V reported diffs"
    bin=$(rpm -ql '"$pkg"' | grep -E "^/usr/(local/)?bin/" | head -1)
    if [ -n "$bin" ]; then
      timeout 20 "$bin" --version >/tmp/smoke.log 2>&1; rc=$?
      echo "--- SMOKE $bin rc=$rc (GUI/Chromium rc=133/1 in a headless container is expected; rc=0 is a real smoke)"; head -2 /tmp/smoke.log
      ldd "$bin" 2>/dev/null | grep -i "not found" && echo "--- LDD-MISSING" || echo "--- LDD OK"
    else
      echo "--- no /usr/bin binary (library/data pkg); ldd scan of shipped ELFs:"
      for e in $(rpm -ql '"$pkg"' | grep -E "\.so|/lib64/" | head -10); do ldd "$e" 2>/dev/null | grep -i "not found"; done
      echo "--- LDD SCAN DONE (no output above = clean)"
    fi
    exit 0
  '
  rc=$?
  echo "=== ROTATE $pkg rc=$rc"
  [ "$rc" = 0 ] || fail=1
done
exit $fail
