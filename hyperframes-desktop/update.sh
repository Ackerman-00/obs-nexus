#!/bin/bash
cd "$(dirname "$0")" || exit 1
SPEC_FILE="hyperframes-desktop.spec"
CHANGES_FILE="hyperframes-desktop.changes"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"
UPSTREAM_URL="https://static.heygen.ai/hyperframes-oss/desktop/HyperFrames-amd64.deb"

echo "Checking for HyperFrames desktop updates..."
curl -fsSL -I --max-time 30 "$UPSTREAM_URL" >/dev/null 2>&1 || { echo "Upstream unavailable."; exit 1; }
tmpd=$(mktemp -d); trap 'rm -rf "$tmpd"' EXIT
curl -fsSL --retry 3 --connect-timeout 30 "$UPSTREAM_URL" -o "$tmpd/up.deb"
NEW_VERSION=$(dpkg-deb -f "$tmpd/up.deb" Version | tr '+' '.')
NEW_SHA=$(sha256sum "$tmpd/up.deb" | awk '{print $1}')

if [ -z "$NEW_VERSION" ]; then echo "Could not read version."; exit 1; fi

CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')
CURRENT_SHA=$(grep -E "^# sha256:" "$SPEC_FILE" | head -1 | awk '{print $3}')

if [ "$CURRENT_VERSION" = "$NEW_VERSION" ]; then
  if [ -z "$CURRENT_SHA" ] || [ "$NEW_SHA" = "$CURRENT_SHA" ]; then
    echo "Already up to date ($CURRENT_VERSION)."
    # ensure cached artifact
    if [ ! -f "hyperframes-desktop.deb" ]; then cp "$tmpd/up.deb" "hyperframes-desktop.deb"; fi
    # ensure the Debtransform wrapper tarball exists (same class as
    # freebuff-desktop 2026-10-27: sync_files would delete the only OBS copy
    # of a locally-built wrapper that download_files cannot regenerate).
    [ -f "hyperframes-desktop-${CURRENT_VERSION}.tar.gz" ] \
      || tar -czf "hyperframes-desktop-${CURRENT_VERSION}.tar.gz" "hyperframes-desktop.deb"
    exit 0
  fi
  # Same-version respin (2026-10-27: upstream re-uploaded the b500 .deb at
  # 14:40Z, x-amz-version-id changed). Re-pin + refresh the payload, but do
  # NOT prepend a duplicate debian.changelog entry for an unchanged version
  # (that would give two <ver>-1 entries and break the Debian recipe) -
  # same handling as cline/omnirush respin.
  echo "Upstream respinned $CURRENT_VERSION (sha256 $CURRENT_SHA -> $NEW_SHA); re-pinning, no debian.changelog entry."
  cp "$tmpd/up.deb" "hyperframes-desktop.deb"
  sed -i -E "s|^# sha256:.*|# sha256:  $NEW_SHA|" "$SPEC_FILE"
  # refresh the wrapper tarball unconditionally: an existing tarball would
  # otherwise keep shipping the PREVIOUS payload bytes
  tar -czf "hyperframes-desktop-${CURRENT_VERSION}.tar.gz" "hyperframes-desktop.deb"
  C=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
  NEWENTRY="-------------------------------------------------------------------\n$C - $PACKAGER_ADDR\n\n- upstream respin of $CURRENT_VERSION (sha256 $CURRENT_SHA ->\n  $NEW_SHA), payload + Debtransform tarball refreshed, version unchanged\n\n"
  [ -f "$CHANGES_FILE" ] && printf "%b%s" "$NEWENTRY" "$(cat $CHANGES_FILE)" > "$CHANGES_FILE" || printf "%b" "$NEWENTRY" > "$CHANGES_FILE"
  echo "Respinned $CURRENT_VERSION."
  exit 0
fi

echo "Update $CURRENT_VERSION -> $NEW_VERSION"
cp "$tmpd/up.deb" "hyperframes-desktop.deb"
sed -i -E "s/^Version:.*/Version:        $NEW_VERSION/" "$SPEC_FILE"
grep -q "^# sha256:" "$SPEC_FILE" || sed -i -E "/^Version:/a # sha256:  $NEW_SHA" "$SPEC_FILE"
sed -i -E "s/^# sha256:.*/# sha256:  $NEW_SHA/" "$SPEC_FILE"

DSC_FILE="hyperframes-desktop.dsc"
sed -i -E "s/^Version: .*/Version: $NEW_VERSION/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: hyperframes-desktop-$NEW_VERSION.tar.gz|" "$DSC_FILE"
tar -czf "hyperframes-desktop-${NEW_VERSION}.tar.gz" "hyperframes-desktop.deb" 2>/dev/null
OLD=$(ls hyperframes-desktop-*.tar.gz 2>/dev/null | grep -v "$NEW_VERSION")
[ -n "$OLD" ] && rm -f $OLD

D=$(date -R -u)
printf 'hyperframes-desktop (%s-1) unstable; urgency=medium\n\n  * New upstream release %s.\n\n -- %s <noreply@example.com>  %s\n\n' "$NEW_VERSION" "$NEW_VERSION" "$PACKAGER" "$D" > /tmp/_debcl.tmp
[ -f debian.changelog ] && cat debian.changelog >> /tmp/_debcl.tmp
mv /tmp/_debcl.tmp debian.changelog

C=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEWENTRY="-------------------------------------------------------------------\n$C - $PACKAGER_ADDR\n\n- version $NEW_VERSION-0\n- Update hyperframes-desktop to $NEW_VERSION\n\n"
[ -f "$CHANGES_FILE" ] && printf "%b%s" "$NEWENTRY" "$(cat $CHANGES_FILE)" > "$CHANGES_FILE" || printf "%b" "$NEWENTRY" > "$CHANGES_FILE"

echo "Successfully updated to $NEW_VERSION."
