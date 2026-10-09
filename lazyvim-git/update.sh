#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="lazyvim-git.spec"
CHANGES_FILE="lazyvim-git.changes"
GITHUB_REPO="LazyVim/LazyVim"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"
VERSION_FILE="lua/lazyvim/config/init.lua"

echo "Checking for upstream updates on $GITHUB_REPO..."

if [ -n "$GITHUB_TOKEN" ]; then
    API_RESPONSE=$(curl -sL -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/commits/main")
else
    API_RESPONSE=$(curl -sL "https://api.github.com/repos/$GITHUB_REPO/commits/main")
fi

LATEST_COMMIT=$(echo "$API_RESPONSE" | jq -r '.sha')
LATEST_DATE_RAW=$(echo "$API_RESPONSE" | jq -r '.commit.committer.date')

if [ -z "$LATEST_COMMIT" ] || [ "$LATEST_COMMIT" == "null" ]; then
    echo "Error: Failed to fetch LazyVim commit from GitHub. Check API limits or connection."
    exit 1
fi

# Base version: LazyVim stopped tagging releases (last tag v9.9.1 is from
# 2023); the authoritative version is the release-please managed
# M.version in lua/lazyvim/config/init.lua at the pinned commit.
LATEST_BASE=$(curl -fsSL "https://raw.githubusercontent.com/$GITHUB_REPO/$LATEST_COMMIT/$VERSION_FILE" | grep -oE 'M\.version = "[0-9]+\.[0-9]+\.[0-9]+"' | head -1 | sed 's/.*"\(.*\)"/\1/')

if [ -z "$LATEST_BASE" ]; then
    echo "Error: Failed to parse base version from $VERSION_FILE."
    exit 1
fi

CURRENT_COMMIT=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')
CURRENT_BASE=$(grep -E "^%global base_version" "$SPEC_FILE" | awk '{print $3}')
SHORT_COMMIT=${LATEST_COMMIT:0:7}
LATEST_DATE=$(echo "$LATEST_DATE_RAW" | sed 's/[-T:Z]//g')

UP_TO_DATE=0
if [ "$CURRENT_COMMIT" == "$LATEST_COMMIT" ] && [ "$CURRENT_BASE" == "$LATEST_BASE" ]; then
    UP_TO_DATE=1
fi

# The Source0 tarball is gitignored and never present in CI checkouts. Always
# ensure it exists locally so the OBS sync step can upload it; if OBS ever
# loses the tarball while the commit is unchanged, this prevents a rebuild
# failure. The version guard above stays a pure commit/base comparison.
if [ -f "lazyvim-$SHORT_COMMIT.tar.gz" ] && [ "$UP_TO_DATE" -eq 1 ]; then
    echo "Package is already at the latest commit ($SHORT_COMMIT) and base version ($LATEST_BASE). No update needed."
    exit 0
fi

if [ "$CURRENT_BASE" != "$LATEST_BASE" ]; then
    echo "Base version update: $CURRENT_BASE -> $LATEST_BASE"
fi
if [ "$CURRENT_COMMIT" != "$LATEST_COMMIT" ] || ! [ -f "lazyvim-$SHORT_COMMIT.tar.gz" ]; then
    echo "Downloading source tarball ($SHORT_COMMIT)..."
    rm -f lazyvim-*.tar.gz
    curl -fsSL --retry 3 --connect-timeout 20 "https://github.com/$GITHUB_REPO/archive/$LATEST_COMMIT.tar.gz" -o "lazyvim-$SHORT_COMMIT.tar.gz" \
        || { echo "❌ Download failed; spec left untouched."; exit 1; }
    if ! [ -s "lazyvim-$SHORT_COMMIT.tar.gz" ] || ! tar -tzf "lazyvim-$SHORT_COMMIT.tar.gz" > /dev/null 2>&1; then
        echo "❌ Downloaded tarball is empty or corrupt; spec left untouched."
        exit 1
    fi
fi

if [ "$UP_TO_DATE" -eq 1 ]; then
    echo "Version unchanged but tarball refreshed; only the artifact needs re-syncing to OBS."
    exit 0
fi

sed -i -E "s/^%global commit.*/%global commit          $LATEST_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global shortcommit.*/%global shortcommit     $SHORT_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global gitdate.*/%global gitdate         $LATEST_DATE/" "$SPEC_FILE"
sed -i -E "s/^%global base_version.*/%global base_version    $LATEST_BASE/" "$SPEC_FILE"
sed -i -E "s/^Version:.*/Version:        %{base_version}+git%{gitdate}.%{shortcommit}/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

# Debian_Testing recipe: keep the .dsc template Version/Tar and the
# debian/changelog head in sync (the snapshot tarball lifecycle above is
# shared with the RPM flow, no extra download). Template Version mirrors
# the spec's macro Version with values substituted.
DSC_FILE="lazyvim-git.dsc"
DSC_VER="${LATEST_BASE}+git${LATEST_DATE}.${SHORT_COMMIT}"
sed -i -E "s/^Version: .*/Version: $DSC_VER/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: lazyvim-$SHORT_COMMIT.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="lazyvim-git ($DSC_VER-1) unstable; urgency=medium\n\n  * New upstream snapshot $SHORT_COMMIT (base $LATEST_BASE).\n\n -- $PACKAGER  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

echo "Generating OBS changes file..."
FORMATTED_DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
if [ "$CURRENT_BASE" != "$LATEST_BASE" ]; then
    ENTRY_NOTE="- Update to base version $LATEST_BASE (Commit: $SHORT_COMMIT)"
else
    ENTRY_NOTE="- Nightly sync with upstream main branch (Commit: $SHORT_COMMIT)"
fi
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$FORMATTED_DATE - $PACKAGER\n\n$ENTRY_NOTE\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! LazyVim updated to $LATEST_BASE (Commit: $SHORT_COMMIT). Ready for OBS sync."