#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="noctalia.spec"
CHANGES_FILE="noctalia.changes"
GITHUB_REPO="noctalia-dev/noctalia"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

# Retry on transient network/API failures so one hiccup does not stub the
# version and abort the whole update.
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
LATEST_TAGVER="${LATEST_TAG#v}"

if [ -z "$LATEST_TAGVER" ] || [ "$LATEST_TAGVER" == "null" ]; then
    echo "Error: Failed to fetch Noctalia version from GitHub. Check API limits or connection."
    exit 1
fi

# Convert upstream tag to RPM version: dashes become tildes for pre-release ordering
# e.g. 5.0.0-beta.7 -> 5.0.0~beta.7 (openSUSE convention). NEVER strip dots:
# a past revision removed the dot before the last component (5.0.1 -> 5.01),
# which sorts NEWER in rpm vercmp and disagrees with every other packager.
LATEST_VER=$(echo "$LATEST_TAGVER" | sed 's/-/~/g')

CURRENT_VER=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')
CURRENT_TAGVER=$(grep -E "^%global tagver" "$SPEC_FILE" | awk '{print $3}')

if [ "$CURRENT_TAGVER" == "$LATEST_TAGVER" ]; then
    echo "Package is already up to date ($CURRENT_TAGVER). No update needed."
    exit 0
fi

echo "Update found: $CURRENT_TAGVER -> $LATEST_TAGVER (version: $LATEST_VER)"

# 0. Download and VERIFY the source tarball BEFORE touching the spec.
echo "Downloading source tarball ($LATEST_TAGVER)..."
rm -f noctalia-*.tar.gz
curl -fsSL --retry 3 --connect-timeout 20 "https://github.com/$GITHUB_REPO/archive/refs/tags/$LATEST_TAG/noctalia-$LATEST_TAGVER.tar.gz" \
    -o "noctalia-$LATEST_TAGVER.tar.gz" \
    || { echo "❌ Download failed; spec left untouched."; exit 1; }
if ! [ -s "noctalia-$LATEST_TAGVER.tar.gz" ] || ! tar -tzf "noctalia-$LATEST_TAGVER.tar.gz" > /dev/null 2>&1; then
    echo "❌ Downloaded tarball is empty or corrupt; spec left untouched."
    exit 1
fi

# 1. Update the spec file (tagver + Version)
sed -i -E "s/^%global tagver.*/%global tagver $LATEST_TAGVER/" "$SPEC_FILE"
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

echo "Success! Noctalia updated to $LATEST_VER. Ready for OBS sync."
