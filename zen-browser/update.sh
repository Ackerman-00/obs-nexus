#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

# ==========================================
# zen-browser Auto-Updater strictly for Git
# ==========================================

SPEC_FILE="zen-browser.spec"
CHANGES_FILE="zen-browser.changes"
REPO="zen-browser/desktop"

echo "🔍 Checking for updates..."

# Get latest release tag from GitHub API (authenticated to avoid rate limits).
# Retry on transient network/API failures so one hiccup does not stub the
# version and abort the whole update.
LATEST_TAG=""
for attempt in 1 2 3; do
    if [ -n "$GITHUB_TOKEN" ]; then
        RESP=$(curl -s --retry 3 --connect-timeout 15 -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$REPO/releases/latest")
    else
        RESP=$(curl -s --retry 3 --connect-timeout 15 "https://api.github.com/repos/$REPO/releases/latest")
    fi
    LATEST_TAG=$(echo "$RESP" | jq -r '.tag_name')
    if [ -n "$LATEST_TAG" ] && [ "$LATEST_TAG" != "null" ]; then
        break
    fi
    echo "   Retry $attempt: could not fetch latest tag from GitHub..."
    sleep 5
done
NEW_VER="${LATEST_TAG#v}"

# Only accept a plausible semantic version (prevents "null"/API-error stub versions)
if [ -z "$NEW_VER" ] || [ "$NEW_VER" == "null" ] || ! echo "$NEW_VER" | grep -qE '^[0-9]'; then
    echo "❌ Error: Could not fetch a valid latest version from GitHub."
    exit 1
fi

# Check current local version using the .spec file
CURRENT_VER=$(grep "^Version:" "$SPEC_FILE" | awk '{print $2}')

# Debian_Testing recipe helper: fetch the upstream tarball under its
# versioned orig name (content-identical rename, no recompression). The
# tarball is gitignored (*.tar.xz) and rides the OBS sync; per-package
# actions/cache in update-packages.yml keeps it across fresh CI checkouts.
fetch_orig_tarball() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/upstream.tar.xz" \
        || { echo "orig tarball download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    mv "$tmpd/upstream.tar.xz" "zen-browser-$ver.tar.xz"
    for old in zen-browser-*.tar.xz; do
        [ "$old" = "zen-browser-$ver.tar.xz" ] || rm -f "$old"
    done
    ls -l "zen-browser-$ver.tar.xz"
    trap - EXIT
    rm -rf "$tmpd"
}

zen_url_for() {
    echo "https://github.com/zen-browser/desktop/releases/download/$1/zen.linux-x86_64.tar.xz"
}

# Orig-tarball guard: fresh CI checkouts start without the gitignored
# tarball (actions/cache usually restores it). Rebuild when missing so an
# OBS sync can never wipe the remote copy with nothing to re-upload.
# NOTE: upstream tags carry a varying prefix (1.23.1b lives under a
# non-v tag); try the stored tag forms newest-first.
if [ ! -f "zen-browser-$CURRENT_VER.tar.xz" ]; then
    echo "Orig tarball missing locally; rebuilding..."
    ( fetch_orig_tarball "$CURRENT_VER" "$(zen_url_for "$CURRENT_VER")" || \
      fetch_orig_tarball "$CURRENT_VER" "$(zen_url_for "v$CURRENT_VER")" ) || \
        echo "WARNING: orig tarball rebuild failed; continuing version check."
fi

echo "   📂 Current Local: $CURRENT_VER"
echo "   ☁️  Latest Online: $NEW_VER"

if [ "$NEW_VER" == "$CURRENT_VER" ]; then
    echo "✅ Package is already up to date."
    exit 0
fi

echo "🚀 New version found! Testing download URL..."
DOWNLOAD_URL="https://github.com/zen-browser/desktop/releases/download/${LATEST_TAG}/zen.linux-x86_64.tar.xz"
HTTP_STATUS=$(curl -o /dev/null -s -w "%{http_code}\n" -I "$DOWNLOAD_URL" -L)

if [ "$HTTP_STATUS" -ne 200 ]; then
    echo "❌ Error: Download URL returned status $HTTP_STATUS. Asset might not be uploaded yet."
    exit 1
fi

echo "⚙️ Updating $SPEC_FILE..."
# Update Spec version and reset the release number to 0
sed -i "s/^Version:.*/Version:        $NEW_VER/" "$SPEC_FILE"
sed -i "s/^Release:.*/Release:        0/" "$SPEC_FILE"

# Debian_Testing recipe: refresh the orig tarball + keep .dsc/changelog
# in sync (DOWNLOAD_URL verified 200 above).
fetch_orig_tarball "$NEW_VER" "$DOWNLOAD_URL"
DSC_FILE="zen-browser.dsc"
sed -i "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: zen-browser-$NEW_VER.tar.xz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="zen-browser ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- Ackerman-00  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

echo "📝 Updating changelog ($CHANGES_FILE)..."
# Manually generate the OBS/RPM changelog format since we aren't using osc
CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="* $CURRENT_DATE GitHub Actions <actions@github.com> - $NEW_VER-0\n- Update zen-browser to v$NEW_VER\n\n"

# Prepend the new entry to the changes file
if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "🎉 Success! Git files updated to v$NEW_VER. Ready for GitHub Action to commit."
