#!/bin/bash
cd "$(dirname "$0")" || exit 1
SPEC_FILE="freebuff-desktop.spec"
CHANGES_FILE="freebuff-desktop.changes"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"
API_URL="https://freebuff.com/api/desktop/download/linux"

echo "Checking for Freebuff desktop updates..."
tmpd=$(mktemp -d); trap 'rm -rf "$tmpd"' EXIT
FINAL_URL=$(curl -fsSL -L --connect-timeout 30 --max-time 180 -o "$tmpd/up.deb" -w '%{url_effective}' "$API_URL" 2>"$tmpd/curl.err") || { echo "Upstream download failed:"; cat "$tmpd/curl.err"; exit 1; }
if [ ! -s "$tmpd/up.deb" ]; then echo "Empty download."; exit 1; fi
NEW_VERSION=$(dpkg-deb -f "$tmpd/up.deb" Version)
if [ -z "$NEW_VERSION" ]; then echo "Could not read .deb version."; exit 1; fi
NEW_SHA=$(sha256sum "$tmpd/up.deb" | awk '{print $1}')

CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')
CURRENT_SHA=$(grep -E "^# sha256:" "$SPEC_FILE" | head -1 | awk '{print $3}')

if [ "$CURRENT_VERSION" = "$NEW_VERSION" ]; then
  if [ -z "$CURRENT_SHA" ] || [ "$NEW_SHA" = "$CURRENT_SHA" ]; then
    echo "Already up to date ($CURRENT_VERSION)."
    if [ ! -f "freebuff-desktop.deb" ]; then cp "$tmpd/up.deb" "freebuff-desktop.deb"; fi
    exit 0
  fi
  echo "sha drift; bumping."
fi

echo "Update $CURRENT_VERSION -> $NEW_VERSION"
cp "$tmpd/up.deb" "freebuff-desktop.deb"
sed -i -E "s/^Version:.*/Version:        $NEW_VERSION/" "$SPEC_FILE"
grep -q "^# sha256:" "$SPEC_FILE" || sed -i -E "/^Version:/a # sha256:  $NEW_SHA" "$SPEC_FILE"
sed -i -E "s/^# sha256:.*/# sha256:  $NEW_SHA/" "$SPEC_FILE"
sed -i -E "s|Source0:.*|Source0:        https://github.com/CodebuffAI/codebuff-community/releases/download/freebuff-desktop-v$NEW_VERSION/Freebuff-$NEW_VERSION-linux-amd64.deb|" "$SPEC_FILE"

DSC_FILE="freebuff-desktop.dsc"
sed -i -E "s/^Version: .*/Version: $NEW_VERSION/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: freebuff-desktop-$NEW_VERSION.tar.gz|" "$DSC_FILE"
tar -czf "freebuff-desktop-${NEW_VERSION}.tar.gz" "freebuff-desktop.deb" 2>/dev/null

D=$(date -R -u)
printf 'freebuff-desktop (%s-1) unstable; urgency=medium\n\n  * New upstream release %s.\n\n -- %s <noreply@example.com>  %s\n\n' "$NEW_VERSION" "$NEW_VERSION" "$PACKAGER" "$D" > /tmp/_debcl.tmp
[ -f debian.changelog ] && cat debian.changelog >> /tmp/_debcl.tmp
mv /tmp/_debcl.tmp debian.changelog

C=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEWENTRY="-------------------------------------------------------------------\n$C - $PACKAGER_ADDR\n\n- version $NEW_VERSION-0\n- Update freebuff-desktop to v$NEW_VERSION\n\n"
[ -f "$CHANGES_FILE" ] && printf "%b%s" "$NEWENTRY" "$(cat $CHANGES_FILE)" > "$CHANGES_FILE" || printf "%b" "$NEWENTRY" > "$CHANGES_FILE"

echo "Successfully updated to $NEW_VERSION."
