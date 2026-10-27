#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="fluxer.spec"
CHANGES_FILE="fluxer.changes"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"
API_URL="https://api.fluxer.app/dl/desktop/stable/linux/x64/latest/rpm"
RPM_FILE="fluxer.rpm"

echo "Checking for fluxer updates..."

HEADER=$(curl -s -D - -o /dev/null -L "$API_URL" 2>/dev/null)
VERSION=$(echo "$HEADER" | grep -i "^X-Fluxer-Version:" | awk '{print $2}' | tr -d '\r')
DISP_VERSION=$(echo "$HEADER" | grep -i "content-disposition:" | grep -oiP 'Fluxer-\K[0-9.]+' | tail -1)
if [ -n "$DISP_VERSION" ] && [ "$DISP_VERSION" != "$VERSION" ]; then
    echo "Note: X-Fluxer-Version=$VERSION vs served filename=$DISP_VERSION, using $DISP_VERSION (filename authoritative)."
    VERSION="$DISP_VERSION"
fi

if [ -z "$VERSION" ]; then
    echo "Error: Failed to fetch upstream version."
    exit 1
fi

CURRENT_VERSION=$(grep "^Version:" "$SPEC_FILE" | awk '{print $2}')

if [ -f "$RPM_FILE" ] && [ "$CURRENT_VERSION" = "$VERSION" ]; then
    CURRENT_SHA=$(grep -E "^# sha256:" "$SPEC_FILE" | head -1 | awk '{print $3}')
    CACHED_SHA=$(sha256sum "$RPM_FILE" | awk '{print $1}')
    if [ -n "$CURRENT_SHA" ] && [ "$CACHED_SHA" != "$CURRENT_SHA" ]; then
        echo "Cached fluxer.rpm sha256 ($CACHED_SHA) != spec pin ($CURRENT_SHA); re-downloading."
    else
        if [ -z "$CURRENT_SHA" ]; then
            echo "Adopting sha256 pin for cached RPM: $CACHED_SHA"
            sed -i "/^Source0:/a # sha256:  $CACHED_SHA" "$SPEC_FILE"
        fi
        echo "Package is already at $VERSION (sha256: $CACHED_SHA). No update needed."
        if [ ! -f "fluxer-$VERSION.tar.gz" ]; then
            tar -czf "fluxer-$VERSION.tar.gz" "$RPM_FILE"
        fi
        exit 0
    fi
fi

echo "Downloading RPM..."
FINAL_NAME=$(curl -s -D - -o /dev/null -L "$API_URL" 2>/dev/null | grep -i "^content-disposition:" | tail -1 | grep -oiE 'filename="[^"]+"' | tail -1)
if echo "$FINAL_NAME" | grep -qi canary; then
    echo "Upstream stable endpoint currently serves a canary build ($FINAL_NAME); holding at $CURRENT_VERSION."
    exit 0
fi
curl -fsSL --retry 3 --connect-timeout 30 -o "$RPM_FILE" "$API_URL" \
    || { echo "RPM download failed; spec left untouched."; exit 1; }
if ! [ -s "$RPM_FILE" ] || ! rpm -qp "$RPM_FILE" >/dev/null 2>&1; then
    echo "Downloaded file is empty or not a valid RPM; spec left untouched."
    rm -f "$RPM_FILE"
    exit 1
fi

INTERNAL_VERSION=$(rpm -qp --queryformat '%{VERSION}' "$RPM_FILE" 2>/dev/null | tr -d '\r')
if [ -n "$INTERNAL_VERSION" ] && [ "$INTERNAL_VERSION" != "$VERSION" ]; then
    echo "Note: transport metadata advertised $VERSION but the served rpm is internally $INTERNAL_VERSION; using the rpm's own version so the label matches the shipped bytes."
    VERSION="$INTERNAL_VERSION"
fi

tar -czf "fluxer-$VERSION.tar.gz" "$RPM_FILE"
for old in fluxer-*.tar fluxer-*.tar.gz; do
    [ "$old" = "fluxer-$VERSION.tar.gz" ] || rm -f "$old"
done

NEW_SHA=$(sha256sum "$RPM_FILE" | awk '{print $1}')
if grep -q "^# sha256:" "$SPEC_FILE"; then
    sed -i "s/^# sha256:.*/# sha256:  $NEW_SHA/" "$SPEC_FILE"
else
    sed -i "/^Source0:/a # sha256:  $NEW_SHA" "$SPEC_FILE"
fi

if [ "$CURRENT_VERSION" = "$VERSION" ]; then
    echo "Version unchanged but RPM refreshed; only the artifact needs re-syncing to OBS."
    exit 0
fi

echo "Update available: $CURRENT_VERSION -> $VERSION"

sed -i "s/^Version:.*/Version:        $VERSION/" "$SPEC_FILE"
sed -i "s/^Release:.*/Release:        0/" "$SPEC_FILE"

DSC_FILE="fluxer.dsc"
sed -i "s/^Version: .*/Version: $VERSION/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: fluxer-$VERSION.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="fluxer ($VERSION-1) unstable; urgency=medium\n\n  * New upstream release $VERSION.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $VERSION-0\n- Update fluxer to v$VERSION\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $VERSION."