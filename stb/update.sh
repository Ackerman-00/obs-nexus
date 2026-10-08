#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="stb.spec"
CHANGES_FILE="stb.changes"
GITHUB_REPO="nothings/stb"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

# stb has no tags or releases, only commits - use the commits API
if [ -n "$GITHUB_TOKEN" ]; then
    API_RESPONSE=$(curl -sL -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/commits/master")
else
    API_RESPONSE=$(curl -sL "https://api.github.com/repos/$GITHUB_REPO/commits/master")
fi

LATEST_COMMIT=$(echo "$API_RESPONSE" | jq -r '.sha')
COMMIT_DATE=$(echo "$API_RESPONSE" | jq -r '.commit.committer.date')

if [ -z "$LATEST_COMMIT" ] || [ "$LATEST_COMMIT" == "null" ]; then
    echo "Error: Failed to fetch stb commit from GitHub. Check API limits or connection."
    exit 1
fi

# Version is the commit date in UTC+8 (matches the date the source snapshot
# was taken on the next day in local time), e.g. 2026-04-15T20:53:29Z -> 20260416
LATEST_VER=$(TZ=Etc/GMT-8 date -d "$COMMIT_DATE" +%Y%m%d)

CURRENT_VER=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

if [ "$CURRENT_VER" == "$LATEST_VER" ]; then
    echo "Package is already up to date ($CURRENT_VER). No update needed."
    exit 0
fi

echo "Update found: $CURRENT_VER -> $LATEST_VER"

# 0. Download and VERIFY the source before touching the spec.
echo "Downloading source tarball ($LATEST_VER, commit $LATEST_COMMIT)..."
rm -f stb-*.tar.xz stb-*.tar.gz
curl -fsSL --retry 3 --connect-timeout 20 "https://github.com/$GITHUB_REPO/archive/$LATEST_COMMIT.tar.gz" -o "stb-$LATEST_VER.tar.gz" \
    || { echo "❌ Download failed; spec left untouched."; exit 1; }
if ! [ -s "stb-$LATEST_VER.tar.gz" ] || ! tar -tzf "stb-$LATEST_VER.tar.gz" > /dev/null 2>&1; then
    echo "❌ Downloaded tarball is empty or corrupt; spec left untouched."
    exit 1
fi

# 1. Update the spec file
sed -i -E "s/^Version:.*/Version:        $LATEST_VER/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

# 2. Repackage the source as .tar.xz (GitHub archives use the commit sha as dir name)
tar -xzf "stb-$LATEST_VER.tar.gz"
mv "stb-$LATEST_COMMIT" "stb-$LATEST_VER"
tar -cJf "stb-$LATEST_VER.tar.xz" "stb-$LATEST_VER"
rm -rf "stb-$LATEST_VER" "stb-$LATEST_VER.tar.gz"

# 3. Generate OBS Changes File
echo "Generating OBS changes file..."
FORMATTED_DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$FORMATTED_DATE - $PACKAGER\n\n- Update to upstream commit $LATEST_COMMIT (version $LATEST_VER)\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! stb updated to $LATEST_VER. Ready for OBS sync."
