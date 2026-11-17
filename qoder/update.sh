#!/bin/bash
cd "$(dirname "$0")" || exit 1
curl() { command curl --connect-timeout 20 --max-time 900 "$@"; }

SPEC_FILE="qoder.spec"
CHANGES_FILE="qoder.changes"
DSC_FILE="qoder.dsc"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"
FEED_BASE="https://download.qoder.com.cn/qoder-app/releases"
FEED="$FEED_BASE/latest-linux.yml"

fetch_manifest() {
  curl -fsSL --retry 3 --connect-timeout 30 --max-time 60 "$1" 2>/dev/null
}

manifest_ver() {
  printf '%s\n' "$1" | sed -n 's/^version: *//p' | head -1
}

echo "Checking for Qoder updates..."
YML=$(fetch_manifest "$FEED") || {
  echo "Upstream feed unavailable."; exit 1; }

FEED_VER=$(manifest_ver "$YML")
[ -n "$FEED_VER" ] || { echo "Could not read version from feed."; exit 1; }

CHOSEN_VER="$FEED_VER"
MAJOR="${FEED_VER%%.*}"
REST="${FEED_VER#*.}"
MINOR="${REST%%.*}"
PATCH="${REST##*.}"
CANDIDATES=""
for offset in 1 2 3 4 5; do
  CANDIDATES="$CANDIDATES $MAJOR.$MINOR.$((PATCH + offset))"
done
for offset in 1 2; do
  CANDIDATES="$CANDIDATES $MAJOR.$((MINOR + offset)).0"
done
for cand in $CANDIDATES; do
  cyml=$(fetch_manifest "$FEED_BASE/$cand/latest-linux.yml") || continue
  [ "$(manifest_ver "$cyml")" = "$cand" ] || continue
  printf '%s\n' "$cyml" | grep -q 'Qoder-linux-amd64\.deb' || continue
  if [ "$cand" != "$CHOSEN_VER" ]; then
    echo "Newer published release found: $cand (channel manifest still says $FEED_VER)"
  fi
  CHOSEN_VER="$cand"
  YML="$cyml"
done
DEB_URL=$(printf '%s\n' "$YML" | grep -E '^[[:space:]]*-? ?url: .*Qoder-linux-amd64\.deb' | head -1 \
          | sed -E 's/.*url: *//; s/^"//; s/"$//')
NEW_SHA=$(printf '%s\n' "$YML" | awk -v u="$DEB_URL" '
  $0 ~ u {seen=1; next}
  seen && /sha256:/ {print $2; exit}')
[ -n "$CHOSEN_VER" ] || { echo "Could not read version from feed."; exit 1; }
[ -n "$DEB_URL" ] || { echo "Could not read the amd64 .deb URL from the feed."; exit 1; }
[ -n "$NEW_SHA" ] || { echo "Could not read the sha256 for the amd64 .deb."; exit 1; }
NEW_VER="${CHOSEN_VER#*:}"

CURRENT_VER=$(grep -E '^Version:' "$SPEC_FILE" | awk '{print $2}')
CURRENT_SHA=$(grep -E '^# sha256:' "$SPEC_FILE" | head -1 | awk '{print $3}')
[ -n "$CURRENT_VER" ] || { echo "Could not read Version from $SPEC_FILE."; exit 1; }

refresh_artifacts() {
  local ver="$1" url="$2" want="${3:-$NEW_SHA}" tmpd got deb_ver
  tmpd=$(mktemp -d)
  curl -fsSL --retry 3 --connect-timeout 30 --max-time 900 "$url" -o "$tmpd/Qoder-linux-amd64.deb" || {
    rm -rf "$tmpd"; echo "orig .deb download failed."; return 1; }
  got=$(sha256sum "$tmpd/Qoder-linux-amd64.deb" | awk '{print $1}')
  if [ -n "$want" ] && [ "$got" != "$want" ]; then
    echo "checksum mismatch: expected $want, download is $got"
    rm -rf "$tmpd"; return 1
  fi
  deb_ver=$(dpkg-deb -f "$tmpd/Qoder-linux-amd64.deb" Version) || { rm -rf "$tmpd"; return 1; }
  if [ "${deb_ver#*:}" != "$ver" ]; then
    echo "version disagreement: feed says $ver, .deb control says $deb_ver"
    rm -rf "$tmpd"; return 1
  fi
  cp "$tmpd/Qoder-linux-amd64.deb" qoder.deb
  rm -rf "$tmpd"
  tar -czf "qoder-$ver.tar.gz" qoder.deb || return 1
  for old in qoder-*.tar.gz; do
    [ "$old" = "qoder-$ver.tar.gz" ] || rm -f "$old"
  done
  ls -l "qoder-$ver.tar.gz"
}

if [ ! -f "qoder-$CURRENT_VER.tar.gz" ]; then
  echo "Debtransform wrapper missing locally; rebuilding..."
  CUR_URL=$(grep -E '^Source0:' "$SPEC_FILE" | awk '{print $2}')
  refresh_artifacts "$CURRENT_VER" "$CUR_URL" "$CURRENT_SHA" || \
    echo "WARNING: wrapper rebuild failed; continuing version check."
fi

if [ "$CURRENT_VER" = "$NEW_VER" ]; then
  if [ -z "$CURRENT_SHA" ] || [ "$NEW_SHA" = "$CURRENT_SHA" ]; then
    echo "Already up to date ($CURRENT_VER)."
    if [ ! -f "qoder.deb" ] || [ ! -f "qoder-$CURRENT_VER.tar.gz" ]; then
      refresh_artifacts "$CURRENT_VER" "$DEB_URL" "$CURRENT_SHA" || exit 1
    fi
    exit 0
  fi
  echo "Upstream respinned $CURRENT_VER (sha256 $CURRENT_SHA -> $NEW_SHA); re-pinning, no debian.changelog entry."
  refresh_artifacts "$CURRENT_VER" "$DEB_URL" "$NEW_SHA" || exit 1
  sed -i -E "s|^# sha256:.*|# sha256: $NEW_SHA|" "$SPEC_FILE"
  C=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
  NEWENTRY="-------------------------------------------------------------------\n$C - $PACKAGER_ADDR\n\n- upstream respin of $CURRENT_VER (sha256 $CURRENT_SHA ->\n  $NEW_SHA), payload + Debtransform tarball refreshed, version unchanged\n\n"
  [ -f "$CHANGES_FILE" ] && printf "%b%s" "$NEWENTRY" "$(cat "$CHANGES_FILE")" > "$CHANGES_FILE" || printf "%b" "$NEWENTRY" > "$CHANGES_FILE"
  echo "Respinned $CURRENT_VER."
  exit 0
fi

echo "Update $CURRENT_VER -> $NEW_VER"
refresh_artifacts "$NEW_VER" "$DEB_URL" "$NEW_SHA" || exit 1

sed -i -E "s/^Version:.*/Version:        $NEW_VER/" "$SPEC_FILE"
sed -i -E "s|^Source0:.*|Source0:        $DEB_URL|" "$SPEC_FILE"
grep -q '^# sha256:' "$SPEC_FILE" || sed -i -E "/^Version:/a # sha256: $NEW_SHA" "$SPEC_FILE"
sed -i -E "s|^# sha256:.*|# sha256: $NEW_SHA|" "$SPEC_FILE"

sed -i -E "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: qoder-$NEW_VER.tar.gz|" "$DSC_FILE"

D=$(date -R -u)
printf 'qoder (%s-1) unstable; urgency=medium\n\n  * New upstream release %s.\n\n -- %s <noreply@example.com>  %s\n\n' \
  "$NEW_VER" "$NEW_VER" "$PACKAGER" "$D" > /tmp/_qoder_cl.tmp
[ -f debian.changelog ] && cat debian.changelog >> /tmp/_qoder_cl.tmp
mv /tmp/_qoder_cl.tmp debian.changelog

C=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEWENTRY="-------------------------------------------------------------------\n$C - $PACKAGER_ADDR\n\n- version $NEW_VER-0\n- Update qoder to $NEW_VER\n\n"
[ -f "$CHANGES_FILE" ] && printf "%b%s" "$NEWENTRY" "$(cat "$CHANGES_FILE")" > "$CHANGES_FILE" || printf "%b" "$NEWENTRY" > "$CHANGES_FILE"

echo "Successfully updated to $NEW_VER."
