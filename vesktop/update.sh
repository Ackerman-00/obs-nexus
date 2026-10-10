#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="vesktop.spec"
CHANGES_FILE="vesktop.changes"
REPO="Vencord/Vesktop"

echo "🔍 Checking for updates..."

# Get latest release data (authenticated to avoid rate limits).
# Retry on transient network/API failures so one hiccup does not stub the
# version and abort the whole update.
LATEST_TAG=""
LATEST_JSON=""
for attempt in 1 2 3; do
    if [ -n "$GITHUB_TOKEN" ]; then
        RESP=$(curl -s --retry 3 --connect-timeout 15 -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$REPO/releases/latest")
    else
        RESP=$(curl -s --retry 3 --connect-timeout 15 "https://api.github.com/repos/$REPO/releases/latest")
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
    echo "❌ Error: Could not fetch latest version."
    exit 1
fi

CURRENT_VER=$(grep "^Version:" "$SPEC_FILE" | awk '{print $2}')

echo "   📂 Current Local: $CURRENT_VER"
echo "   ☁️  Latest Online: $NEW_VER"

# Debian_Testing recipe helper: wrap an upstream .rpm into the
# gzip-compressed debtransform orig input (dpkg-source 3.0 (quilt) rejects
# an uncompressed .orig.tar). The wrapper is gitignored (*.tar.gz) and
# rides the OBS sync; per-package actions/cache in update-packages.yml
# keeps it across fresh CI checkouts.
build_orig_wrapper() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/upstream.rpm" \
        || { echo "❌ orig RPM download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -czf "vesktop-$ver.tar.gz" -C "$tmpd" upstream.rpm
    for old in vesktop-*.tar vesktop-*.tar.gz; do
        [ "$old" = "vesktop-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "vesktop-$ver.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
}

# Orig-tarball guard: fresh CI checkouts start without the gitignored
# wrapper (actions/cache usually restores it). Rebuild from the current
# spec Source0 URL when missing so an OBS sync can never wipe the remote
# copy with nothing to re-upload.
if [ ! -f "vesktop-$CURRENT_VER.tar.gz" ]; then
    echo "   Orig wrapper missing locally; rebuilding..."
    CUR_URL=$(grep "^Source0:" "$SPEC_FILE" | awk '{print $2}')
    build_orig_wrapper "$CURRENT_VER" "$CUR_URL" || \
        echo "   WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$NEW_VER" == "$CURRENT_VER" ]; then
    echo "✅ Package is already up to date."
    exit 0
fi

# Filter GitHub assets specifically for Vencord's exact syntax: .x86_64.rpm
DOWNLOAD_URL=$(echo "$LATEST_JSON" | jq -r '.assets[] | select(.name | test("\\.x86_64\\.rpm$")) | .browser_download_url' | head -n 1)

if [ -z "$DOWNLOAD_URL" ] || [ "$DOWNLOAD_URL" == "null" ]; then
    echo "❌ Error: Could not find x86_64 RPM in release."
    exit 1
fi

echo "🚀 New version found! Updating $SPEC_FILE..."
sed -i "s|^Version:.*|Version:        $NEW_VER|" "$SPEC_FILE"
sed -i "s|^Release:.*|Release:        0|" "$SPEC_FILE"
sed -i "s|^Source0:.*|Source0:        $DOWNLOAD_URL|" "$SPEC_FILE"

# Debian_Testing recipe: refresh the wrapper + keep .dsc/changelog in sync.
build_orig_wrapper "$NEW_VER" "$DOWNLOAD_URL"
DSC_FILE="vesktop.dsc"
sed -i "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: vesktop-$NEW_VER.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="vesktop ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- Ackerman-00  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

echo "📝 Updating changelog..."
CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="* $CURRENT_DATE GitHub Actions <actions@github.com> - $NEW_VER-0\n- Update vesktop to v$NEW_VER\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "🎉 Success! Git files updated to v$NEW_VER. Ready for commit."
