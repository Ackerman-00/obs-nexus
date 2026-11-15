#!/bin/bash
cd "$(dirname "$0")" || exit 1
curl() { command curl --connect-timeout 20 --max-time 900 "$@"; }

SPEC_FILE="mixtapes.spec"
CHANGES_FILE="mixtapes.changes"
GITHUB_REPO="m-obeid/Mixtapes"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

if [ -n "$GITHUB_TOKEN" ]; then
    API_RESPONSE=$(curl -sL -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/commits/main")
else
    API_RESPONSE=$(curl -sL "https://api.github.com/repos/$GITHUB_REPO/commits/main")
fi

LATEST_COMMIT=$(echo "$API_RESPONSE" | jq -r '.sha')
LATEST_DATE_RAW=$(echo "$API_RESPONSE" | jq -r '.commit.committer.date')

if [ -z "$LATEST_COMMIT" ] || [ "$LATEST_COMMIT" == "null" ]; then
    echo "Error: Failed to fetch master/main commit from GitHub."
    exit 1
fi

SHORT_COMMIT=${LATEST_COMMIT:0:7}
GITDATE=$(echo "$LATEST_DATE_RAW" | sed 's/[-T:Z]//g')
CURRENT_COMMIT=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')

if [ "$CURRENT_COMMIT" == "$LATEST_COMMIT" ] && [ -f "mixtapes-$SHORT_COMMIT.tar.gz" ]; then
    echo "Package is already at the latest commit ($SHORT_COMMIT). No update needed."
    exit 0
fi

echo "New commit: ${CURRENT_COMMIT:0:7} -> $SHORT_COMMIT"

TARBALL="mixtapes-$SHORT_COMMIT.tar.gz"

if [ "$CURRENT_COMMIT" != "$LATEST_COMMIT" ] || ! [ -f "$TARBALL" ]; then
    echo "Downloading source tarball ($SHORT_COMMIT)..."
    rm -f mixtapes-*.tar.gz
    curl -fsSL --retry 3 --connect-timeout 30 "https://github.com/$GITHUB_REPO/archive/$LATEST_COMMIT.tar.gz" -o "mixtapes-$SHORT_COMMIT.tar.gz" \
        || { echo "❌ Download failed; spec left untouched."; exit 1; }
    if ! [ -s "$TARBALL" ] || ! tar -tzf "$TARBALL" > /dev/null 2>&1; then
        echo "❌ Downloaded tarball is empty or corrupt; spec left untouched."; exit 1
    fi
fi

sed -i -E "s/^%global commit.*/%global commit          $LATEST_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global shortcommit.*/%global shortcommit     $SHORT_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global gitdate.*/%global gitdate         $GITDATE/" "$SPEC_FILE"
sed -i -E "s/^Version:.*/Version:        %{base_version}+git%{gitdate}.%{shortcommit}/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version 0+git${GITDATE}.${SHORT_COMMIT}-0\n- Port from fedora-nexus; Mixtapes Rust rewrite (gtk4 / libadwaita / WebKitGTK 6.0)\n\n"
if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! mixtapes at $SHORT_COMMIT. Ready for OBS sync."
