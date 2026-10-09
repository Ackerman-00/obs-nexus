#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash fluxer/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="fluxer.spec"
CHANGES_FILE="fluxer.changes"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"
API_URL="https://api.fluxer.app/dl/desktop/stable/linux/x64/latest/rpm"
RPM_FILE="fluxer.rpm"

echo "Checking for fluxer updates..."

# The X-Fluxer-Version header on the 302 sometimes lags the artifact actually
# served (observed 2026-09-20: header advertised 2026.920.41250 while the
# served stable RPM was fluxer-2026.920.41303). The Content-Disposition
# filename of the served RPM is authoritative — prefer it when they differ.
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

# The Source0 RPM is gitignored and never present in CI checkouts. Always
# ensure it exists locally so the OBS sync step can upload it; if OBS ever
# loses the RPM while the version is unchanged, this prevents a rebuild
# failure. The version guard above stays a pure version comparison.
if [ -f "$RPM_FILE" ] && [ "$CURRENT_VERSION" = "$VERSION" ]; then
    echo "Package is already at $VERSION. No update needed."
    # Keep the Debian orig wrapper in step (no download needed here).
    if [ ! -f "fluxer-$VERSION.tar.gz" ]; then
        tar -czf "fluxer-$VERSION.tar.gz" "$RPM_FILE"
    fi
    exit 0
fi

echo "Downloading RPM..."
# Stable channel must never package a canary build: upstream sometimes
# redirects the stable endpoint to canary during channel migrations
# (observed 2026-09-10: stable -> .../canary/.../Fluxer-Canary-*.rpm
# while x-fluxer-version still advertised a stable-looking number).
# Refuse and HOLD instead of shipping canary as stable.
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

# Debian_Testing recipe: (re)build the debtransform orig wrapper (gzip-compressed
# tar holding the upstream RPM; dpkg-source 3.0 (quilt) rejects uncompressed
# .orig.tar, so the wrapper MUST stay compressed) whenever the RPM was
# (re)downloaded above -- this covers version bumps AND same-version
# refreshes. The wrapper is gitignored (*.tar.gz) and rides the OBS sync;
# per-package actions/cache in update-packages.yml keeps it across fresh CI
# checkouts.
tar -czf "fluxer-$VERSION.tar.gz" "$RPM_FILE"
for old in fluxer-*.tar fluxer-*.tar.gz; do
    [ "$old" = "fluxer-$VERSION.tar.gz" ] || rm -f "$old"
done

if [ "$CURRENT_VERSION" = "$VERSION" ]; then
    echo "Version unchanged but RPM refreshed; only the artifact needs re-syncing to OBS."
    exit 0
fi

echo "Update available: $CURRENT_VERSION -> $VERSION"

sed -i "s/^Version:.*/Version:        $VERSION/" "$SPEC_FILE"
sed -i "s/^Release:.*/Release:        0/" "$SPEC_FILE"

# Debian_Testing recipe: keep the .dsc Version/Tar and debian/changelog in sync.
DSC_FILE="fluxer.dsc"
sed -i "s/^Version: .*/Version: $VERSION/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: fluxer-$VERSION.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="fluxer ($VERSION-1) unstable; urgency=medium\n\n  * New upstream release $VERSION.\n\n -- $PACKAGER  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="* $CURRENT_DATE $PACKAGER - $VERSION-0\n- Update fluxer to v$VERSION\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $VERSION."