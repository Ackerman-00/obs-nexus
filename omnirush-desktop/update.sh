#!/bin/bash
cd "$(dirname "$0")" || exit 1
SPEC_FILE="omnirush-desktop.spec"
CHANGES_FILE="omnirush-desktop.changes"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"
REPO="omnirush-ai/omnirush-gui"

echo "Checking for OmniRush updates..."
LATEST=$(curl -s -m 20 "https://api.github.com/repos/$REPO/releases/latest")
LATEST_TAG=$(printf '%s' "$LATEST" | grep -oP '"tag_name":\s*"\K[^"]+')
if [ -z "$LATEST_TAG" ] || [ "$LATEST_TAG" = "null" ]; then echo "Error fetching version."; exit 1; fi
LATEST_VERSION=$(echo "$LATEST_TAG" | sed 's/^v//;s@-@.@g')

CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')
if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
  if [ -f omnirush-linux-amd64-${CURRENT_VERSION}.deb ] 2>/dev/null; then echo "Already up to date ($CURRENT_VERSION)."; exit 0; fi
fi

ASSET_URL=$(curl -s -m 20 "https://api.github.com/repos/$REPO/releases/tags/$LATEST_TAG" \
  | grep -oP '"browser_download_url":\s*"\K[^"]+omnirush-linux-amd64-[^"]+\.deb' | head -1)
if [ -z "$ASSET_URL" ]; then echo "Asset not found."; exit 1; fi
HTTP=$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 30 "$ASSET_URL")
if [ "$HTTP" != "200" ]; then echo "Asset HTTP $HTTP; not bumping."; exit 0; fi

echo "Update $CURRENT_VERSION -> $LATEST_VERSION"
DEBNAME="omnirush-linux-amd64-${LATEST_VERSION}.deb"
curl -fsSL --retry 3 --connect-timeout 30 "$ASSET_URL" -o "$DEBNAME"
sed -i -E "s/^Version:.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
sed -i -E "s|Source0:.*|Source0:        $ASSET_URL|" "$SPEC_FILE"

DSC_FILE="omnirush-desktop.dsc"
sed -i -E "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: omnirush-desktop-$LATEST_VERSION.tar.gz|" "$DSC_FILE"

tar -czf "omnirush-desktop-${LATEST_VERSION}.tar.gz" "$DEBNAME" 2>/dev/null

D=$(date -R -u)
printf 'omnirush-desktop (%s-1) unstable; urgency=medium\n\n  * New upstream release %s.\n\n -- %s <noreply@example.com>  %s\n\n' "$LATEST_VERSION" "$LATEST_VERSION" "$PACKAGER" "$D" > /tmp/_debcl.tmp
[ -f debian.changelog ] && cat debian.changelog >> /tmp/_debcl.tmp
mv /tmp/_debcl.tmp debian.changelog

C=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
NEWENTRY="-------------------------------------------------------------------\n$C - $PACKAGER_ADDR\n\n- version $LATEST_VERSION-0\n- Update omnirush-desktop to v$LATEST_VERSION\n\n"
[ -f "$CHANGES_FILE" ] && printf "%b%s" "$NEWENTRY" "$(cat $CHANGES_FILE)" > "$CHANGES_FILE" || printf "%b" "$NEWENTRY" > "$CHANGES_FILE"

echo "Successfully updated to $LATEST_VERSION."
