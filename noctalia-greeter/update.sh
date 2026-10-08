#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="noctalia-greeter.spec"
CHANGES_FILE="noctalia-greeter.changes"
GITHUB_REPO="noctalia-dev/noctalia-greeter"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

# Greeter has no GitHub "releases" (only tags), so use the tags API
if [ -n "$GITHUB_TOKEN" ]; then
    API_RESPONSE=$(curl -sL -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/tags")
else
    API_RESPONSE=$(curl -sL "https://api.github.com/repos/$GITHUB_REPO/tags")
fi

LATEST_TAG=$(echo "$API_RESPONSE" | jq -r '.[0].name')
LATEST_VER="${LATEST_TAG#v}"

if [ -z "$LATEST_VER" ] || [ "$LATEST_VER" == "null" ]; then
    echo "Error: Failed to fetch Noctalia Greeter version from GitHub. Check API limits or connection."
    exit 1
fi

CURRENT_VER=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

if [ "$CURRENT_VER" == "$LATEST_VER" ]; then
    echo "Package is already up to date ($CURRENT_VER). No update needed."
    exit 0
fi

echo "Update found: $CURRENT_VER -> $LATEST_VER"

# 0. Download and VERIFY the source tarball BEFORE touching the spec.
echo "Downloading source tarball ($LATEST_VER)..."
rm -f noctalia-greeter-*.tar.gz
curl -fsSL --retry 3 --connect-timeout 20 "https://github.com/$GITHUB_REPO/archive/refs/tags/$LATEST_TAG/noctalia-greeter-$LATEST_VER.tar.gz" \
    -o "noctalia-greeter-$LATEST_VER.tar.gz" \
    || { echo "❌ Download failed; spec left untouched."; exit 1; }
if ! [ -s "noctalia-greeter-$LATEST_VER.tar.gz" ] || ! tar -tzf "noctalia-greeter-$LATEST_VER.tar.gz" > /dev/null 2>&1; then
    echo "❌ Downloaded tarball is empty or corrupt; spec left untouched."
    exit 1
fi

# 1. Update the spec file
sed -i -E "s/^Version:.*/Version:        $LATEST_VER/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

# 2. Generate OBS Changes File
echo "Generating OBS changes file..."
FORMATTED_DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$FORMATTED_DATE - $PACKAGER\n\n- Update to upstream version $LATEST_VER\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! Noctalia Greeter updated to $LATEST_VER. Ready for OBS sync."
