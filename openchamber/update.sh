#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="openchamber.spec"
CHANGES_FILE="openchamber.changes"
GITHUB_REPO="openchamber/openchamber"
PACKAGER="Ackerman-00"

# Upstream layout: release tag v<ver>, Linux asset
# OpenChamber-<ver>-linux-x86_64.AppImage (note: version WITHOUT v prefix
# in the filename, unlike the tag).
echo "Checking for upstream updates on $GITHUB_REPO..."

# Get latest release data (authenticated to avoid rate limits).
# Retry on transient network/API failures so one hiccup does not stub the
# version and abort the whole update.
LATEST_TAG=""
LATEST_JSON=""
for attempt in 1 2 3; do
    if [ -n "$GITHUB_TOKEN" ]; then
        RESP=$(curl -s --retry 3 --connect-timeout 15 -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/releases/latest")
    else
        RESP=$(curl -s --retry 3 --connect-timeout 15 "https://api.github.com/repos/$GITHUB_REPO/releases/latest")
    fi
    LATEST_TAG=$(echo "$RESP" | jq -r '.tag_name')
    if [ -n "$LATEST_TAG" ] && [ "$LATEST_TAG" != "null" ]; then
        LATEST_JSON="$RESP"
        break
    fi
    echo "   Retry $attempt: could not fetch latest tag from GitHub..."
    sleep 5
done
NEW_VER="${LATEST_TAG#v}"

if [ -z "$NEW_VER" ] || [ "$NEW_VER" == "null" ]; then
    echo "Error: Could not fetch latest version."
    exit 1
fi

CURRENT_VER=$(grep "^Version:" "$SPEC_FILE" | awk '{print $2}')

echo "   Current Local: $CURRENT_VER"
echo "   Latest Online: $NEW_VER"

X86_APPIMAGE="OpenChamber-$NEW_VER-linux-x86_64.AppImage"

# Debian_Testing recipe helper: wrap upstream artifact(s) into the
# gzip-compressed debtransform orig input. dpkg-source 3.0 (quilt) REJECTS
# an uncompressed .orig.tar ("unrecognized file for a v2.0 source
# package", Debian_Testing 2026-10-09) - same fix as localsend. The
# wrapper is gitignored (*.tar.gz) and rides the OBS sync; per-package
# actions/cache in update-packages.yml keeps it across fresh CI
# checkouts.
build_orig_wrapper() {
    local ver="$1"; shift
    tar -czf "openchamber-$ver.tar.gz" "$@"
    for old in openchamber-*.tar.gz; do
        [ "$old" = "openchamber-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "openchamber-$ver.tar.gz"
}

# Orig-tarball guard: fresh CI checkouts start without the gitignored
# wrapper (actions/cache usually restores it). Rebuild from the current
# release asset when missing so an OBS sync can never wipe the remote copy
# with nothing to re-upload.
if [ ! -f "openchamber-$CURRENT_VER.tar.gz" ]; then
    echo "Orig wrapper missing locally; rebuilding..."
    CUR_IMG="OpenChamber-$CURRENT_VER-linux-x86_64.AppImage"
    # NOTE: the downloaded AppImage is deliberately KEPT (not rm'd): the
    # RPM flow's bare-filename Source0 must be uploaded by the OBS sync,
    # so deleting it here would break the Tumbleweed build.
    curl -fsSL --retry 3 --connect-timeout 30 \
        "https://github.com/$GITHUB_REPO/releases/download/v$CURRENT_VER/$CUR_IMG" \
        -o "$CUR_IMG" && build_orig_wrapper "$CURRENT_VER" "$CUR_IMG" || \
        echo "WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$NEW_VER" == "$CURRENT_VER" ]; then
    echo "Package is already up to date."
    exit 0
fi

# Asset guard: only bump once the Linux x86_64 AppImage really exists
# (releases also ship apk/dmg/exe/vsix/tgz; a blind bump on a tag whose
# AppImage is missing produces a 404 spec).
ASSET_NAMES=$(echo "$LATEST_JSON" | jq -r '.assets[]?.name // empty')
if ! echo "$ASSET_NAMES" | grep -qx "$X86_APPIMAGE"; then
    echo "HOLD: $LATEST_TAG has no Linux x86_64 AppImage ($X86_APPIMAGE missing). Spec stays on $CURRENT_VER."
    exit 0
fi
echo "Linux x86_64 AppImage asset present; proceeding."

echo "New version found! Updating $SPEC_FILE..."
sed -i "s|^Version:.*|Version:        $NEW_VER|" "$SPEC_FILE"
sed -i "s|^Release:.*|Release:        0|" "$SPEC_FILE"

# Download + verify the AppImage BEFORE touching anything else (a failed
# or error-stubbed download must NOT bump or reach OBS).
X86_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/$X86_APPIMAGE"
curl -fsSL --retry 3 --connect-timeout 60 "$X86_URL" -o "$X86_APPIMAGE" \
    || { echo "AppImage download failed; spec left untouched."; exit 1; }
if ! [ -s "$X86_APPIMAGE" ] || ! head -c4 "$X86_APPIMAGE" | grep -q $'\x7fELF'; then
    echo "$X86_APPIMAGE is missing, empty, or not an ELF AppImage; spec left untouched."
    rm -f "$X86_APPIMAGE"
    exit 1
fi

# Debian_Testing recipe: wrap the verified AppImage + keep .dsc/changelog
# in sync.
build_orig_wrapper "$NEW_VER" "$X86_APPIMAGE"
DSC_FILE="openchamber.dsc"
sed -i "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: openchamber-$NEW_VER.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="openchamber ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- $PACKAGER  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

echo "Updating changelog ($CHANGES_FILE)..."
CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="* $CURRENT_DATE $PACKAGER - $NEW_VER-0\n- Update openchamber to v$NEW_VER\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! OpenChamber updated to v$NEW_VER. Ready for OBS sync."
