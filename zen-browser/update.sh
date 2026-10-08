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
