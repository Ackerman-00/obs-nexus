#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="ladybird-unstable.spec"
DSC_FILE="ladybird-unstable.dsc"
CHANGES_FILE="ladybird-unstable.changes"
GITHUB_REPO="LadybirdBrowser/ladybird"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

LATEST_COMMIT=$(git ls-remote "https://github.com/$GITHUB_REPO.git" HEAD 2>/dev/null | awk '{print $1}')
if [ -z "$LATEST_COMMIT" ]; then
    echo "Error: Failed to fetch HEAD commit."
    exit 1
fi

SHORT=${LATEST_COMMIT:0:7}
CURRENT_COMMIT=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')

if [ "$CURRENT_COMMIT" = "$LATEST_COMMIT" ]; then
    echo "Package is already at main $SHORT. No update needed."
    exit 0
fi

COMMIT_DATE_RAW=$(curl -sL -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/commits/$LATEST_COMMIT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('commit',{}).get('committer',{}).get('date',''))" 2>/dev/null)
if [ -z "$COMMIT_DATE_RAW" ]; then
    echo "Error: Failed to fetch the commit date."
    exit 1
fi
GIT_DATE=$(echo "$COMMIT_DATE_RAW" | sed 's/[-T:Z]//g')

BASE_VER=$(grep -E "^%global base_version" "$SPEC_FILE" | awk '{print $3}')
NEW_VER="$BASE_VER+git$GIT_DATE.$SHORT"
TARBALL_URL="https://github.com/$GITHUB_REPO/archive/$LATEST_COMMIT.tar.gz"

echo "   Current: $CURRENT_COMMIT"
echo "   Latest:  $LATEST_COMMIT ($NEW_VER)"

build_debian_orig() {
    local ver="$1" commit="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 60 "$TARBALL_URL" -o "$tmpd/main.tar.gz" \
        || { echo "upstream source download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -tzf "$tmpd/main.tar.gz" > /dev/null \
        || { echo "upstream source corrupt."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -czf "ladybird-unstable-$ver.tar.gz" -C "$tmpd" "ladybird-$commit" \
        || { echo "orig tarball pack failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    for old in ladybird-unstable-*.tar.gz; do
        [ "$old" = "ladybird-unstable-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "ladybird-unstable-$ver.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
}

build_debian_orig "$NEW_VER" "$LATEST_COMMIT" || exit 1

NEW_SHA=$(curl -fsSL --retry 3 --connect-timeout 60 "$TARBALL_URL" | sha256sum | awk '{print $1}')

sed -i -E "s/^%global commit.*/%global commit         $LATEST_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global shortcommit.*/%global shortcommit    $SHORT/" "$SPEC_FILE"
sed -i -E "s/^%global gitdate.*/%global gitdate        $GIT_DATE/" "$SPEC_FILE"
sed -i -E "s/^Version:.*/Version:        %{base_version}+git%{gitdate}.%{shortcommit}/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"
sed -i -E "s|^# sha256:.*|# sha256:  $NEW_SHA|" "$SPEC_FILE"

sed -i -E "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: ladybird-unstable-$NEW_VER.tar.gz|" "$DSC_FILE"

DEB_DATE=$(date -R -u)
DEB_ENTRY="ladybird-unstable ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream snapshot $SHORT.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $NEW_VER-0\n- Update ladybird-unstable to main $SHORT\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $NEW_VER."
