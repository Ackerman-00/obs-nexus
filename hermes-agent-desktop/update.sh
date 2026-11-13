#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="hermes-agent-desktop.spec"
DSC_FILE="hermes-agent-desktop.dsc"
CHANGES_FILE="hermes-agent-desktop.changes"
GITHUB_REPO="NousResearch/hermes-agent"
NODE_URL="https://nodejs.org/download/release/v26.12.1/node-v26.12.1-linux-x64.tar.xz"
NODE_SHA256="6170b2d474e1c626f43cff3adc118df9fe3b573258a4fc3d850c8dbc6b079bbd"
PNPM_URL="https://registry.npmjs.org/@pnpm/exe.linux-x64/-/exe.linux-x64-12.15.0.tgz"
PNPM_SHA256="402f7045b1e0587acb1542f18d38afbccb6babf3c7451394e6fb3d9f0160c6ca"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

LATEST_COMMIT=$(git ls-remote "https://github.com/$GITHUB_REPO.git" HEAD 2>/dev/null | awk '{print $1}')
if [ -z "$LATEST_COMMIT" ]; then
    echo "Error: Failed to fetch HEAD commit."
    exit 1
fi

LATEST_TAG=$(git ls-remote --tags "https://github.com/$GITHUB_REPO.git" 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^v0\.[0-9]+\.[0-9]+$' | sort -V | tail -1)
if [ -z "$LATEST_TAG" ]; then
    echo "Error: no stable v0.x.y tag found upstream."
    exit 1
fi

BASE_VER="${LATEST_TAG#v}"
SHORT=${LATEST_COMMIT:0:7}
CURRENT_COMMIT=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')
CURRENT_BASE=$(grep -E "^%global base_version" "$SPEC_FILE" | awk '{print $3}')
CURRENT_GITDATE=$(grep -E "^%global gitdate" "$SPEC_FILE" | awk '{print $3}')
CURRENT_SHORT=$(grep -E "^%global shortcommit" "$SPEC_FILE" | awk '{print $3}')
CURRENT_VER="$CURRENT_BASE+git$CURRENT_GITDATE.$CURRENT_SHORT"

build_debian_orig() {
    local ver="$1" commit="$2" url="$3" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 60 "$url" -o "$tmpd/main.tar.gz" \
        || { echo "upstream source download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -xzf "$tmpd/main.tar.gz" -C "$tmpd" \
        || { echo "upstream source corrupt."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    SRC="$tmpd/hermes-agent-$commit"
    [ -d "$SRC" ] || { echo "unexpected source layout."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    mkdir -p "$SRC/.tools/node" "$SRC/.tools/pnpm"
    curl -fsSL --retry 3 --connect-timeout 120 "$NODE_URL" -o "$tmpd/node.tar.xz" \
        || { echo "node download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    echo "$NODE_SHA256  $tmpd/node.tar.xz" | sha256sum -c --status \
        || { echo "node checksum mismatch."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -xJf "$tmpd/node.tar.xz" -C "$SRC/.tools/node" --strip-components=1
    curl -fsSL --retry 3 --connect-timeout 120 "$PNPM_URL" -o "$tmpd/pnpm.tgz" \
        || { echo "pnpm download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    echo "$PNPM_SHA256  $tmpd/pnpm.tgz" | sha256sum -c --status \
        || { echo "pnpm checksum mismatch."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -xzf "$tmpd/pnpm.tgz" -C "$SRC/.tools/pnpm"
    tar -czf "hermes-agent-desktop-$ver.tar.gz" -C "$tmpd" "hermes-agent-$commit" \
        || { echo "orig tarball pack failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    for old in hermes-agent-desktop-*.tar.gz; do
        [ "$old" = "hermes-agent-desktop-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "hermes-agent-desktop-$ver.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
}

if [ ! -f "hermes-agent-desktop-$CURRENT_VER.tar.gz" ]; then
    echo "  -> Orig tarball missing locally; rebuilding..."
    build_debian_orig "$CURRENT_VER" "$CURRENT_COMMIT" "https://github.com/$GITHUB_REPO/archive/$CURRENT_COMMIT.tar.gz" \
        || echo "  -> WARNING: orig tarball rebuild failed; continuing version check."
fi

if [ "$CURRENT_COMMIT" = "$LATEST_COMMIT" ] && [ "$CURRENT_BASE" = "$BASE_VER" ]; then
    echo "Package is already at main $SHORT (base $BASE_VER). No update needed."
    exit 0
fi

COMMIT_DATE_RAW=$(curl -sL -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/commits/$LATEST_COMMIT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('commit',{}).get('committer',{}).get('date',''))" 2>/dev/null)
if [ -z "$COMMIT_DATE_RAW" ]; then
    echo "Error: Failed to fetch the commit date."
    exit 1
fi
GIT_DATE=$(echo "$COMMIT_DATE_RAW" | sed 's/[-T:Z]//g')
NEW_VER="$BASE_VER+git$GIT_DATE.$SHORT"
TARBALL_URL="https://github.com/$GITHUB_REPO/archive/$LATEST_COMMIT.tar.gz"

echo "   Current: $CURRENT_BASE+git.$CURRENT_COMMIT"
echo "   Latest:  $NEW_VER"

build_debian_orig "$NEW_VER" "$LATEST_COMMIT" "$TARBALL_URL" || exit 1

NEW_SHA=$(curl -fsSL --retry 3 --connect-timeout 60 "$TARBALL_URL" | sha256sum | awk '{print $1}')

sed -i -E "s/^%global commit.*/%global commit          $LATEST_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global shortcommit.*/%global shortcommit     $SHORT/" "$SPEC_FILE"
sed -i -E "s/^%global gitdate.*/%global gitdate         $GIT_DATE/" "$SPEC_FILE"
sed -i -E "s/^%global base_version.*/%global base_version    $BASE_VER/" "$SPEC_FILE"
sed -i -E "s/^Version:.*/Version:        %{base_version}+git%{gitdate}.%{shortcommit}/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"
sed -i -E "s|^# sha256:.*|# sha256:  $NEW_SHA|" "$SPEC_FILE"

sed -i -E "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: hermes-agent-desktop-$NEW_VER.tar.gz|" "$DSC_FILE"

DEB_DATE=$(date -R -u)
DEB_ENTRY="hermes-agent-desktop ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream snapshot $SHORT (base $BASE_VER).\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $NEW_VER-0\n- Update hermes-agent-desktop to base $BASE_VER + main $SHORT\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $NEW_VER."
