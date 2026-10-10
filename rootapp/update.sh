#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="rootapp.spec"
CHANGES_FILE="rootapp.changes"
PACKAGER="Ackerman-00"
APPIMAGE_URL="https://installer.rootapp.com/installer/Linux/X64/Root.AppImage"

echo "Checking for rootapp updates..."

TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

curl -fsSL --retry 3 --connect-timeout 20 -o "$TMPDIR/Root.AppImage" "$APPIMAGE_URL" \
    || { echo "❌ AppImage download failed; spec left untouched."; exit 1; }
if ! [ -s "$TMPDIR/Root.AppImage" ] || ! head -c4 "$TMPDIR/Root.AppImage" | grep -q $'\x7fELF'; then
    echo "❌ Downloaded AppImage is empty or not an ELF; spec left untouched."
    exit 1
fi
NEW_SHA=$(sha256sum "$TMPDIR/Root.AppImage" | awk '{print $1}')

CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')
CURRENT_SHA=$(grep -E "^# sha256:" "$SPEC_FILE" | awk '{print $3}')

# Debian_Testing recipe helper: wrap the upstream AppImage into the
# gzip-compressed debtransform orig input (dpkg-source 3.0 (quilt) rejects
# an uncompressed .orig.tar). The wrapper is gitignored (*.tar.gz) and
# rides the OBS sync; per-package actions/cache in update-packages.yml
# keeps it across fresh CI checkouts.
build_orig_wrapper() {
    local ver="$1" img="$2"
    tar -czf "rootapp-$ver.tar.gz" -C "$(dirname "$img")" "$(basename "$img")"
    for old in rootapp-*.tar rootapp-*.tar.gz; do
        [ "$old" = "rootapp-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "rootapp-$ver.tar.gz"
}

if [ -n "$CURRENT_SHA" ] && [ "$NEW_SHA" = "$CURRENT_SHA" ]; then
    echo "Package is up to date (sha256: $CURRENT_SHA)."
    # Orig-tarball guard: fresh CI checkouts start without the gitignored
    # wrapper (actions/cache usually restores it). Rebuild it here from the
    # just-downloaded AppImage so an OBS sync can never wipe the remote copy
    # with nothing to re-upload.
    if [ ! -f "rootapp-$CURRENT_VERSION.tar.gz" ]; then
        build_orig_wrapper "$CURRENT_VERSION" "$TMPDIR/Root.AppImage"
    fi
    exit 0
fi

echo "Downloaded AppImage SHA256: $NEW_SHA"
if [ -n "$CURRENT_SHA" ]; then
    echo "Previous SHA256: $CURRENT_SHA"
fi
echo "Update detected."

VERSION=""
EXTRACTED=0

if command -v unsquashfs &>/dev/null; then
    OFFSET=$(od -An -N8 -t u8 -j 40 "$TMPDIR/Root.AppImage" | tr -d ' ')
    MAGIC=$(dd if="$TMPDIR/Root.AppImage" bs=1 skip=$OFFSET count=4 2>/dev/null)

    if [ "$MAGIC" != "hsqs" ]; then
        OFFSET=$(python3 -c "
with open('$TMPDIR/Root.AppImage', 'rb') as f:
    d = f.read()
    p = d.find(b'hsqs', 200000)
    print(p if p >= 0 else 0)
")
    fi

    dd if="$TMPDIR/Root.AppImage" bs=$OFFSET skip=1 of="$TMPDIR/squashfs.img" 2>/dev/null
    unsquashfs -d "$TMPDIR/squashfs-root" -f "$TMPDIR/squashfs.img" >/dev/null 2>&1

    if [ -d "$TMPDIR/squashfs-root" ]; then
        EXTRACTED=1
    fi
fi

if [ "$EXTRACTED" = "1" ]; then
    ROOT="$TMPDIR/squashfs-root"

    # .NET/Avalonia apps: version lives in sq.version (NuSpec XML).
    # This is the ONLY authoritative source for Root App versions.
    if [ -f "$ROOT/usr/bin/sq.version" ]; then
        VERSION=$(python3 -c "
import xml.etree.ElementTree as ET
try:
    root = ET.parse('$ROOT/usr/bin/sq.version').getroot()
    ns = {'ns': 'http://schemas.microsoft.com/packaging/2010/07/nuspec.xsd'}
    m = root.find('.//ns:metadata/ns:version', ns)
    if m is not None and m.text:
        print(m.text)
    else:
        m2 = root.find('.//metadata/version')
        if m2 is not None and m2.text:
            print(m2.text)
except:
    print('')
")
    fi

    # Electron apps: version in package.json
    if [ -z "$VERSION" ] && [ -f "$ROOT/resources/app/package.json" ]; then
        VERSION=$(python3 -c "
import json
try:
    d = json.load(open('$ROOT/resources/app/package.json'))
    print(d.get('version', ''))
except:
    print('')
")
    fi

    # No wildcard grep - it picks up dependency versions (e.g. Stripe billing SDK "19.2.5").

    rm -rf "$TMPDIR/squashfs-root" "$TMPDIR/squashfs.img"
fi

# Validate extracted version (reject implausible values like dependency versions)
if [ -n "$VERSION" ]; then
    MAJOR="${VERSION%%.*}"
    if [ "$MAJOR" -gt 5 ] 2>/dev/null; then
        echo "ERROR: Extracted version $VERSION has implausible major version $MAJOR"
        VERSION=""
    fi
fi

if [ -n "$VERSION" ] && [ "$VERSION" != "$CURRENT_VERSION" ]; then
    echo "Detected version: $VERSION ($CURRENT_VERSION -> $VERSION)"
    sed -i "s/^Version:.*/Version:        $VERSION/" "$SPEC_FILE"
    sed -i "s/^Release:.*/Release:        0/" "$SPEC_FILE"
else
    VERSION="$CURRENT_VERSION"
    echo "Version unchanged: $VERSION"
fi

if grep -q "^# sha256:" "$SPEC_FILE"; then
    sed -i "s/^# sha256:.*/# sha256: $NEW_SHA/" "$SPEC_FILE"
else
    sed -i "/^Source0:/a # sha256:  $NEW_SHA" "$SPEC_FILE"
fi

# Debian_Testing recipe: refresh the wrapper + keep .dsc/changelog in sync.
build_orig_wrapper "$VERSION" "$TMPDIR/Root.AppImage"
DSC_FILE="rootapp.dsc"
sed -i "s/^Version: .*/Version: $VERSION/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: rootapp-$VERSION.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="rootapp ($VERSION-1) unstable; urgency=medium\n\n  * New upstream release $VERSION.\n\n -- $PACKAGER  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

FORMATTED_DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$FORMATTED_DATE - $PACKAGER\n\n- Update to $VERSION (sha256: $NEW_SHA)\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! RootApp updated to $VERSION. Ready for OBS sync."
