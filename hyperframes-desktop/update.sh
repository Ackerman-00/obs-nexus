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
    exit 0
  fi
  echo "sha drift; bumping."
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

C=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
NEWENTRY="-------------------------------------------------------------------\n$C - $PACKAGER_ADDR\n\n- version $NEW_VERSION-0\n- Update hyperframes-desktop to ${NEW_VERSION%%.*} build\n\n"
[ -f "$CHANGES_FILE" ] && printf "%b%s" "$NEWENTRY" "$(cat $CHANGES_FILE)" > "$CHANGES_FILE" || printf "%b" "$NEWENTRY" > "$CHANGES_FILE"

echo "Successfully updated to $NEW_VERSION."
