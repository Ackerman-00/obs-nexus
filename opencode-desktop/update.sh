#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="opencode-desktop.spec"
CHANGES_FILE="opencode-desktop.changes"
GITHUB_REPO="anomalyco/opencode"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

# Candidate tags newest-first. Upstream sometimes pushes bare tags (e.g. the
# v2.0.x series, which have no GitHub release object and no desktop DEB
# asset). Walk down until a tag whose desktop DEB asset actually exists, so a
# stray asset-less tag can never pin us stale or ship a 404 spec.
ALL_TAGS=$(git ls-remote --tags https://github.com/$GITHUB_REPO.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^v?[0-9]' | sort -uV -r)

if [ -z "$ALL_TAGS" ]; then
    echo "Error: Failed to fetch tags."
    exit 1
fi

CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

LATEST_VERSION=""
for TAG in $ALL_TAGS; do
    CANDIDATE=$(echo "$TAG" | sed 's/^v//')
    if [ "$CANDIDATE" = "$CURRENT_VERSION" ]; then
        echo "Package is already at $CANDIDATE. No update needed."
        exit 0
    fi
    SOURCE_URL="https://github.com/$GITHUB_REPO/releases/download/v$CANDIDATE/opencode-desktop-linux-amd64.deb"
    HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 30 "$SOURCE_URL")
    if [ "$HTTP_CODE" = "200" ]; then
        LATEST_VERSION="$CANDIDATE"
        break
    fi
    echo "Tag v$CANDIDATE has no desktop DEB asset (HTTP $HTTP_CODE); trying older tag..."
done

if [ -z "$LATEST_VERSION" ]; then
    echo "No newer tag with a desktop DEB asset found; staying on $CURRENT_VERSION."
    exit 0
fi

echo "Update found: $CURRENT_VERSION -> $LATEST_VERSION"

# Defensive check: the DEB asset must actually exist before we bump (already
# proven 200 above; re-verify cheaply to close any TOCTOU gap).
SOURCE_URL="https://github.com/$GITHUB_REPO/releases/download/v$LATEST_VERSION/opencode-desktop-linux-amd64.deb"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 30 "$SOURCE_URL")
if [ "$HTTP_CODE" != "200" ]; then
    echo "Release asset $SOURCE_URL returns HTTP $HTTP_CODE (not 200); not bumping to avoid a broken spec."
    echo "Staying on $CURRENT_VERSION."
    exit 0
fi

sed -i "s/^Version:.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
sed -i "s/^Release:.*/Release:        0/" "$SPEC_FILE"

CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="* $CURRENT_DATE $PACKAGER - $LATEST_VERSION-0\n- Update opencode-desktop to v$LATEST_VERSION\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $LATEST_VERSION."
