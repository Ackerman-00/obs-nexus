#!/bin/bash
cd "$(dirname "$0")" || exit 1
curl() { command curl --connect-timeout 20 --max-time 900 "$@"; }

SPEC_FILE="umbriel-git.spec"
CHANGES_FILE="umbriel-git.changes"
GITHUB_REPO="noctalia-dev/umbriel"
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
    echo "Error: Failed to fetch master/main commit from GitHub. Check API limits or connection."
    exit 1
fi

SHORT_COMMIT=${LATEST_COMMIT:0:7}
GITDATE=$(echo "$LATEST_DATE_RAW" | sed 's/[-T:Z]//g')
CURRENT_COMMIT=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')
BASE_VER=$(curl -fsSL "https://raw.githubusercontent.com/$GITHUB_REPO/$LATEST_COMMIT/VERSION" | tr -d '[:space:]' | grep -E '^[0-9]+\.[0-9]+' | head -1)
if [ -z "$BASE_VER" ]; then
    echo "Error: Failed to read base version from VERSION file."
    exit 1
fi

if [ "$CURRENT_COMMIT" = "$LATEST_COMMIT" ]; then
    CURRENT_BASE=$(grep -E "^%global base_version" "$SPEC_FILE" | awk '{print $3}')
    if [ "$CURRENT_BASE" = "$BASE_VER" ]; then
        echo "Package is already at the latest commit ($SHORT_COMMIT, base $BASE_VER). No update needed."
        exit 0
    fi
    CURRENT_BASE="$BASE_VER"
else
    echo "New commit: ${CURRENT_COMMIT:0:7} -> $SHORT_COMMIT"
fi

TARBALL="umbriel-%{base_version}+git%{gitdate}.%{shortcommit}.tar.gz"

if [ "$CURRENT_COMMIT" != "$LATEST_COMMIT" ] || ! [ -f "umbriel-$SHORT_COMMIT.tar.gz" ]; then
    echo "Downloading source tarball ($SHORT_COMMIT)..."
    rm -f umbriel-*.tar.gz
    rm -f umbriel-*.tar.gz
    curl -fsSL --retry 3 --connect-timeout 30 "https://github.com/$GITHUB_REPO/archive/$LATEST_COMMIT.tar.gz" -o "umbriel-$SHORT_COMMIT.tar.gz" \
        || { echo "❌ Download failed; spec left untouched."; exit 1; }
    if ! [ -s "umbriel-$SHORT_COMMIT.tar.gz" ] || ! tar -tzf "umbriel-$SHORT_COMMIT.tar.gz" > /dev/null 2>&1; then
        echo "❌ Downloaded tarball is empty or corrupt; spec left untouched."; exit 1
    fi
fi

sed -i -E "s/^%global commit.*/%global commit          $LATEST_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global shortcommit.*/%global shortcommit     $SHORT_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global gitdate.*/%global gitdate         $GITDATE/" "$SPEC_FILE"
sed -i -E "s/^%global base_version.*/%global base_version    $BASE_VER/" "$SPEC_FILE"
sed -i -E "s/^Version:.*/Version:        %{base_version}+git%{gitdate}.%{shortcommit}/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

DSC_FILE="umbriel-git.dsc"
DSC_VER="${BASE_VER}+git${GITDATE}.${SHORT_COMMIT}"
sed -i -E "s/^Version: .*/Version: ${DSC_VER}/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: umbriel-${SHORT_COMMIT}.tar.gz|" "$DSC_FILE"
TARBALL_NAME="umbriel-${SHORT_COMMIT}.tar.gz"
SHA256=$(sha256sum "$TARBALL_NAME" | awk '{print $1}')
MD5=$(md5sum "$TARBALL_NAME" | awk '{print $1}')
SIZE=$(stat -c%s "$TARBALL_NAME")
sed -i -E '/^(Checksums-Sha256|Checksums-Md5|Files):/,$d' "$DSC_FILE"
printf 'Checksums-Sha256:\n %s %s %s\nFiles:\n %s %s %s\n' "$SHA256" "$SIZE" "$TARBALL_NAME" "$MD5" "$SIZE" "$TARBALL_NAME" >> "$DSC_FILE"

DEB_DATE=$(date -R -u)
DEB_ENTRY="umbriel-git (${DSC_VER}-1) unstable; urgency=medium\n\n  * New upstream snapshot $SHORT_COMMIT (base $BASE_VER).\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version ${DSC_VER}-0\n- Port from fedora-nexus; umbriel builds from git snapshot with Tumbleweed system wlroots and vendored umbrielfx\n\n"
if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! umbriel-git at $BASE_VER + $SHORT_COMMIT. Ready for OBS sync."
