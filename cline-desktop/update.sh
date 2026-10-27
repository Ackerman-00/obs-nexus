#!/bin/bash
cd "$(dirname "$0")" || exit 1
SPEC_FILE="cline-desktop.spec"
CHANGES_FILE="cline-desktop.changes"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"
BASE_URL="https://github.com/cline/cline"
MANIFEST_URL="${BASE_URL}/releases/download/desktop-latest/latest.json"

echo "Checking for Cline desktop updates..."

LATEST_JSON=$(curl -sL -m 60 "$MANIFEST_URL")
if [ -z "$LATEST_JSON" ]; then echo "Error: failed to fetch manifest."; exit 1; fi
LATEST_VERSION=$(printf '%s' "$LATEST_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['version'])")
LATEST_URL=$(printf '%s' "$LATEST_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin)['platforms']['linux-x86_64-deb']['url'])")

if [ -z "$LATEST_VERSION" ]; then echo "Error: no version in manifest."; exit 1; fi

CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

LOCAL_FILE="cline-desktop.deb"

if [ -f "$LOCAL_FILE" ] && [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    CACHED_SHA=$(sha256sum "$LOCAL_FILE" | awk '{print $1}')
    CURRENT_SHA=$(grep -E "^# sha256:" "$SPEC_FILE" | head -1 | awk '{print $3}')
    if [ -z "$CURRENT_SHA" ] || [ "$CACHED_SHA" = "$CURRENT_SHA" ]; then
        echo "Already up to date ($CURRENT_VERSION)."
        exit 0
    fi
    echo "sha mismatch; re-downloading."
fi

HTTP=$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 30 "$LATEST_URL")
if [ "$HTTP" != "200" ]; then echo "Asset returns HTTP $HTTP; not bumping."; exit 0; fi

echo "Update: $CURRENT_VERSION -> $LATEST_VERSION"
curl -fsSL --retry 3 --connect-timeout 30 "$LATEST_URL" -o "$LOCAL_FILE"

NEW_SHA=$(sha256sum "$LOCAL_FILE" | awk '{print $1}')
sed -i -E "s/^Version:.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
sed -i -E "s|Source0:.*|Source0:        $LATEST_URL|" "$SPEC_FILE"
# insert sha pin if missing, then refresh it - a bump without this leaves
# the PREVIOUS version's pin in the spec (fluxer-style drift guard)
grep -q "^# sha256:" "$SPEC_FILE" || sed -i -E "/^Version:/a # sha256:  $NEW_SHA" "$SPEC_FILE"
sed -i -E "s|^# sha256:.*|# sha256:  $NEW_SHA|" "$SPEC_FILE"

DSC_FILE="cline-desktop.dsc"
sed -i -E "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: cline-desktop-$LATEST_VERSION.tar.gz|" "$DSC_FILE"

# wrapper tarball (Debian side)
tar -czf "cline-desktop-${LATEST_VERSION}.tar.gz" "$LOCAL_FILE" 2>/dev/null
OLD=$(ls cline-desktop-*.tar.gz 2>/dev/null | grep -v "$NEW_VERSION")
[ -n "$OLD" ] && rm -f $OLD

D=$(date -R -u)
printf 'cline-desktop (%s-1) unstable; urgency=medium\n\n  * New upstream release %s.\n\n -- %s <noreply@example.com>  %s\n\n' "$LATEST_VERSION" "$LATEST_VERSION" "$PACKAGER" "$D" > /tmp/_debcl.tmp
[ -f debian.changelog ] && cat debian.changelog >> /tmp/_debcl.tmp
mv /tmp/_debcl.tmp debian.changelog

C=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
NEWENTRY="-------------------------------------------------------------------\n$C - $PACKAGER_ADDR\n\n- version $LATEST_VERSION-0\n- Update cline-desktop to v$LATEST_VERSION\n\n"
[ -f "$CHANGES_FILE" ] && printf "%b%s" "$NEWENTRY" "$(cat $CHANGES_FILE)" > "$CHANGES_FILE" || printf "%b" "$NEWENTRY" > "$CHANGES_FILE"

echo "Successfully updated to $LATEST_VERSION."
