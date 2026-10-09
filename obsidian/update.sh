#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="obsidian.spec"
CHANGES_FILE="obsidian.changes"
GITHUB_REPO="obsidianmd/obsidian-releases"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"

# Our packaging format: self-contained Linux AppImages (bundled Electron,
# no system electron - see issue #9). Both arches are required.
#   x86_64:  Obsidian-<ver>.AppImage
#   aarch64: Obsidian-<ver>-arm64.AppImage

echo "🔍 Checking for upstream updates on $GITHUB_REPO..."

# Retry on transient network/API failures so one hiccup does not stub the
# version and abort the whole update.
API_RESPONSE=""
LATEST_TAG=""
for attempt in 1 2 3; do
    if [ -n "$GITHUB_TOKEN" ]; then
        API_RESPONSE=$(curl -sL --retry 3 --connect-timeout 15 -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/releases/latest")
    else
        API_RESPONSE=$(curl -sL --retry 3 --connect-timeout 15 "https://api.github.com/repos/$GITHUB_REPO/releases/latest")
    fi
    LATEST_TAG=$(echo "$API_RESPONSE" | jq -r '.tag_name')
    if [ -n "$LATEST_TAG" ] && [ "$LATEST_TAG" != "null" ]; then
        break
    fi
    echo "   Retry $attempt: could not fetch latest tag from GitHub..."
    sleep 5
done
LATEST_VER="${LATEST_TAG#v}" # Strip the 'v' prefix

if [ -z "$LATEST_VER" ] || [ "$LATEST_VER" == "null" ]; then
    echo "❌ Error: Failed to fetch Obsidian version from GitHub. Check API limits or connection."
    exit 1
fi

CURRENT_VER=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

# Debian_Testing recipe helper: wrap upstream artifact(s) into the
# gzip-compressed debtransform orig input (dpkg-source 3.0 (quilt) rejects
# an uncompressed .orig.tar). The wrapper is gitignored (*.tar.gz) and
# rides the OBS sync; per-package actions/cache in update-packages.yml
# keeps it across fresh CI checkouts.
build_orig_wrapper() {
    local ver="$1"; shift
    tar -czf "obsidian-$ver.tar.gz" "$@"
    for old in obsidian-*.tar obsidian-*.tar.gz; do
        [ "$old" = "obsidian-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "obsidian-$ver.tar.gz"
}

# Orig-tarball guard: fresh CI checkouts start without the gitignored
# wrapper (actions/cache usually restores it). Rebuild from the current
# release assets when missing so an OBS sync can never wipe the remote
# copy with nothing to re-upload. The AppImages are KEPT locally (not
# deleted): they are the spec Source0/Source1, and the pipeline drift-sync
# gate requires every Source artifact to be present before it uploads any
# tracked-file changes (e.g. new debian.* files) -- deleting them here
# would defer the drift-sync forever.
if [ ! -f "obsidian-$CURRENT_VER.tar.gz" ]; then
    echo "Orig wrapper missing locally; rebuilding from release assets..."
    X86_FN="Obsidian-$CURRENT_VER.AppImage"
    ARM_FN="Obsidian-$CURRENT_VER-arm64.AppImage"
    curl -fsSL --retry 3 --connect-timeout 20 \
        "https://github.com/$GITHUB_REPO/releases/download/v$CURRENT_VER/$X86_FN" -o "$X86_FN" && \
    curl -fsSL --retry 3 --connect-timeout 20 \
        "https://github.com/$GITHUB_REPO/releases/download/v$CURRENT_VER/$ARM_FN" -o "$ARM_FN" && \
    build_orig_wrapper "$CURRENT_VER" "$X86_FN" "$ARM_FN" || \
        { echo "WARNING: orig wrapper rebuild failed; continuing version check."; rm -f "$X86_FN" "$ARM_FN"; }
fi

if [ "$CURRENT_VER" == "$LATEST_VER" ]; then
    echo "✅ Package is already up to date ($CURRENT_VER). No update needed."
    exit 0
fi

echo "🚀 Update found: $CURRENT_VER -> $LATEST_VER"

# Asset guard (issue #9 HOLD pattern): if the new release ships no Linux
# assets for our packaging format, SKIP it cleanly (exit 0, spec untouched).
# Real case: v1.13.8 shipped only Obsidian-1.13.8.apk (Android) - no
# AppImage/tarball/deb, so there is nothing Linux to package. A blind bump
# would break the build and wipe good OBS sources.
ASSET_NAMES=$(echo "$API_RESPONSE" | jq -r '.assets[]?.name // empty')
if [ -z "$ASSET_NAMES" ]; then
    echo "⚠️  Could not list release assets; refusing to bump blind. Spec left untouched (HOLD)."
    exit 0
fi
echo "   Release assets:"
echo "$ASSET_NAMES" | sed 's/^/     - /'

X86_APPIMAGE="Obsidian-$LATEST_VER.AppImage"
ARM_APPIMAGE="Obsidian-$LATEST_VER-arm64.AppImage"

if ! echo "$ASSET_NAMES" | grep -qx "$X86_APPIMAGE"; then
    echo "⏸️  HOLD: $LATEST_TAG has no Linux x86_64 AppImage ($X86_APPIMAGE missing - e.g. APK-only mobile release). Spec stays on $CURRENT_VER."
    exit 0
fi
if ! echo "$ASSET_NAMES" | grep -qx "$ARM_APPIMAGE"; then
    echo "⏸️  HOLD: $LATEST_TAG has no Linux aarch64 AppImage ($ARM_APPIMAGE missing). Spec stays on $CURRENT_VER."
    exit 0
fi
echo "✅ Both Linux AppImage assets present; proceeding."

# 0. Download and VERIFY both AppImages BEFORE touching the spec. A failed
#    or error-stubbed download (e.g. rate-limited HTML page) must NOT bump the
#    version or reach OBS - otherwise the sync step uploads a stub and deletes
#    the previous good sources, breaking the build.
echo "📦 Downloading AppImage sources..."
rm -f Obsidian-*.AppImage

X86_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/$X86_APPIMAGE"
ARM_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/$ARM_APPIMAGE"

curl -fsSL --retry 3 --connect-timeout 20 "$X86_URL" -o "$X86_APPIMAGE" \
    || { echo "❌ x86_64 AppImage download failed; OBS sources left untouched."; exit 1; }
curl -fsSL --retry 3 --connect-timeout 20 "$ARM_URL" -o "$ARM_APPIMAGE" \
    || { echo "❌ arm64 AppImage download failed; OBS sources left untouched."; exit 1; }

# Verify both files are real AppImages (ELF) before use.
for f in "$X86_APPIMAGE" "$ARM_APPIMAGE"; do
    if ! [ -s "$f" ] || ! head -c4 "$f" | grep -q $'\x7fELF'; then
        echo "❌ $f is missing, empty, or not an ELF AppImage; OBS sources left untouched."
        exit 1
    fi
done
echo "✅ Both AppImages verified (x86_64 $(du -h "$X86_APPIMAGE" | cut -f1), arm64 $(du -h "$ARM_APPIMAGE" | cut -f1))."

# 1. Update the spec file
sed -i -E "s/^Version:.*/Version:        $LATEST_VER/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

# 1b. Debian_Testing recipe: wrap both verified AppImages + keep
# .dsc/changelog in sync (AppImages downloaded + verified in step 0 above).
build_orig_wrapper "$LATEST_VER" "$X86_APPIMAGE" "$ARM_APPIMAGE"
DSC_FILE="obsidian.dsc"
sed -i -E "s/^Version: .*/Version: $LATEST_VER/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: obsidian-$LATEST_VER.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="obsidian ($LATEST_VER-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VER.\n\n -- $PACKAGER  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

# 2. Generate OBS Changes File
echo "📝 Generating OBS changes file..."
FORMATTED_DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$FORMATTED_DATE - $PACKAGER\n\n- Update to upstream version $LATEST_VER (bundled Electron AppImage)\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "🎉 Success! Obsidian updated to $LATEST_VER. Ready for OBS sync."
