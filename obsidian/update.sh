#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="obsidian.spec"
CHANGES_FILE="obsidian.changes"
GITHUB_REPO="obsidianmd/obsidian-releases"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"


echo "🔍 Checking for upstream updates on $GITHUB_REPO..."

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
LATEST_VER="${LATEST_TAG#v}"

if [ -z "$LATEST_VER" ] || [ "$LATEST_VER" == "null" ]; then
    echo "❌ Error: Failed to fetch Obsidian version from GitHub. Check API limits or connection."
    exit 1
fi

CURRENT_VER=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

build_orig_wrapper() {
    local ver="$1"; shift
    tar -czf "obsidian-$ver.tar.gz" "$@"
    for old in obsidian-*.tar obsidian-*.tar.gz; do
        [ "$old" = "obsidian-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "obsidian-$ver.tar.gz"
}

if [ ! -f "obsidian-$CURRENT_VER.tar.gz" ]; then
    echo "Orig wrapper missing locally; rebuilding from release assets..."
    X86_FN="Obsidian-$CURRENT_VER.AppImage"
    curl -fsSL --retry 3 --connect-timeout 20 \
        "https://github.com/$GITHUB_REPO/releases/download/v$CURRENT_VER/$X86_FN" -o "$X86_FN" && \
    build_orig_wrapper "$CURRENT_VER" "$X86_FN" || \
        { echo "WARNING: orig wrapper rebuild failed; continuing version check."; rm -f "$X86_FN"; }
fi

if [ "$CURRENT_VER" == "$LATEST_VER" ]; then
    echo "✅ Package is already up to date ($CURRENT_VER). No update needed."
    exit 0
fi

echo "🚀 Update found: $CURRENT_VER -> $LATEST_VER"

ASSET_NAMES=$(echo "$API_RESPONSE" | jq -r '.assets[]?.name // empty')
if [ -z "$ASSET_NAMES" ]; then
    echo "⚠️  Could not list release assets; refusing to bump blind. Spec left untouched (HOLD)."
    exit 0
fi
echo "   Release assets:"
echo "$ASSET_NAMES" | sed 's/^/     - /'

X86_APPIMAGE="Obsidian-$LATEST_VER.AppImage"

if ! echo "$ASSET_NAMES" | grep -qx "$X86_APPIMAGE"; then
    echo "⏸️  HOLD: $LATEST_TAG has no Linux x86_64 AppImage ($X86_APPIMAGE missing - e.g. APK-only mobile release). Spec stays on $CURRENT_VER."
    exit 0
fi
echo "✅ Linux x86_64 AppImage asset present; proceeding."

echo "📦 Downloading AppImage sources..."
rm -f Obsidian-*.AppImage

X86_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/$X86_APPIMAGE"

curl -fsSL --retry 3 --connect-timeout 20 "$X86_URL" -o "$X86_APPIMAGE" \
    || { echo "❌ x86_64 AppImage download failed; OBS sources left untouched."; exit 1; }

if ! [ -s "$X86_APPIMAGE" ] || ! head -c4 "$X86_APPIMAGE" | grep -q $'\x7fELF'; then
    echo "❌ $X86_APPIMAGE is missing, empty, or not an ELF AppImage; OBS sources left untouched."
    exit 1
fi
echo "✅ AppImage verified (x86_64 $(du -h "$X86_APPIMAGE" | cut -f1))."

sed -i -E "s/^Version:.*/Version:        $LATEST_VER/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

build_orig_wrapper "$LATEST_VER" "$X86_APPIMAGE"
DSC_FILE="obsidian.dsc"
sed -i -E "s/^Version: .*/Version: $LATEST_VER/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: obsidian-$LATEST_VER.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="obsidian ($LATEST_VER-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VER.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

echo "📝 Generating OBS changes file..."
FORMATTED_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$FORMATTED_DATE - $PACKAGER_ADDR\n\n- Update to upstream version $LATEST_VER (bundled Electron AppImage)\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "🎉 Success! Obsidian updated to $LATEST_VER. Ready for OBS sync."
