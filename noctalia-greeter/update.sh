#!/bin/bash
cd "$(dirname "$0")" || exit 1
. ../tools/upstream-guard.sh
curl() { command curl --connect-timeout 20 --max-time 900 "$@"; }

SPEC_FILE="noctalia-greeter.spec"
CHANGES_FILE="noctalia-greeter.changes"
GITHUB_REPO="noctalia-dev/noctalia-greeter"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

LATEST_TAG=$(git ls-remote --tags https://github.com/$GITHUB_REPO.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^v?[0-9]' | sed -E 's/^v?([0-9].*)/\1 &/' | sort -V -k1,1 | tail -1 | awk '{print $2}')
BASE_VER=$(echo "$LATEST_TAG" | sed 's/^v//')

if [ -z "$BASE_VER" ]; then
    echo "Error: Failed to fetch latest tag."
    exit 1
fi

echo "Latest upstream tag: $LATEST_TAG (base version: $BASE_VER)"

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
CURRENT_BASE=$(grep -E "^%global base_version" "$SPEC_FILE" | awk '{print $3}')

COMMIT_CHANGED=$([ "$CURRENT_COMMIT" != "$LATEST_COMMIT" ] && echo true || echo false)
BASE_VER_CHANGED=$([ "$CURRENT_BASE" != "$BASE_VER" ] && echo true || echo false)

if [ "$COMMIT_CHANGED" == "false" ] && [ "$BASE_VER_CHANGED" == "false" ]; then
    echo "Package is already at the latest commit ($SHORT_COMMIT, base $BASE_VER). No update needed."
    exit 0
fi

[ "$COMMIT_CHANGED" == "true" ] && echo "New commit: ${CURRENT_COMMIT:0:7} -> $SHORT_COMMIT"
[ "$BASE_VER_CHANGED" == "true" ] && echo "Base version bump: $CURRENT_BASE -> $BASE_VER"

if [ "$CURRENT_COMMIT" != "$LATEST_COMMIT" ] || ! [ -f "noctalia-greeter-$SHORT_COMMIT.tar.gz" ]; then
    echo "Downloading source tarball ($SHORT_COMMIT)..."
    rm -f noctalia-greeter-*.tar.gz
    curl -fsSL --retry 3 --connect-timeout 30 "https://github.com/$GITHUB_REPO/archive/$LATEST_COMMIT.tar.gz" -o "noctalia-greeter-$SHORT_COMMIT.tar.gz" \
        || { echo "❌ Download failed; spec left untouched."; exit 1; }
    if ! [ -s "noctalia-greeter-$SHORT_COMMIT.tar.gz" ] || ! tar -tzf "noctalia-greeter-$SHORT_COMMIT.tar.gz" > /dev/null 2>&1; then
        echo "❌ Downloaded tarball is empty or corrupt; spec left untouched."; exit 1
    fi
fi

sed -i -E "s/^%global commit.*/%global commit          $LATEST_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global shortcommit.*/%global shortcommit     $SHORT_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global gitdate.*/%global gitdate         $GITDATE/" "$SPEC_FILE"
sed -i -E "s/^%global base_version.*/%global base_version    $BASE_VER/" "$SPEC_FILE"
sed -i -E "s/^Version:.*/Version:        %{base_version}+git%{gitdate}.%{shortcommit}/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

DSC_FILE="noctalia-greeter.dsc"
DSC_VER="${BASE_VER}+git${GITDATE}.${SHORT_COMMIT}"
sed -i -E "s/^Version: .*/Version: ${DSC_VER}/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: noctalia-greeter-${SHORT_COMMIT}.tar.gz|" "$DSC_FILE"

DEB_DATE=$(date -R -u)
DEB_ENTRY="noctalia-greeter (${DSC_VER}-1) unstable; urgency=medium\n\n  * New upstream snapshot $SHORT_COMMIT (base $BASE_VER).\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version ${DSC_VER}-$(spec_release "$SPEC_FILE")\n- Port from fedora-nexus; greeter built with Tumbleweed system wlroots and vendored wuffs/stb_image_resize2 headers\n\n"
if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! noctalia-greeter at $BASE_VER + $SHORT_COMMIT. Ready for OBS sync."
