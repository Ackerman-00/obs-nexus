#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="hatter-icon-theme.spec"
DSC_FILE="hatter-icon-theme.dsc"
CHANGES_FILE="hatter-icon-theme.changes"
GITHUB_REPO="Mibea/Hatter"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

LATEST_TAG=$(git ls-remote --tags "https://github.com/$GITHUB_REPO.git" 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^V[0-9]+\.[0-9]+$' | sort -V | tail -1)

if [ -z "$LATEST_TAG" ]; then
    echo "Error: Failed to fetch latest tag."
    exit 1
fi

NEW_VER="${LATEST_TAG#V}"
CURRENT_VER=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

echo "   Current Local: $CURRENT_VER"
echo "   Latest Online: $NEW_VER"

fetch_orig_tarball() {
    local ver="$1" tag="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 \
        "https://github.com/$GITHUB_REPO/archive/refs/tags/$tag.tar.gz" \
        -o "$tmpd/upstream.tar.gz" \
        || { echo "orig tarball download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -tzf "$tmpd/upstream.tar.gz" > /dev/null \
        || { echo "orig tarball corrupt."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    cp "$tmpd/upstream.tar.gz" "hatter-icon-theme-$ver.tar.gz"
    for old in hatter-icon-theme-*.tar.gz; do
        [ "$old" = "hatter-icon-theme-$ver.tar.gz" ] || rm -f "$old"
    done
    sha256sum "hatter-icon-theme-$ver.tar.gz" | awk '{print $1}'
    ls -l "hatter-icon-theme-$ver.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
}

if [ ! -f "hatter-icon-theme-$CURRENT_VER.tar.gz" ]; then
    echo "  -> Orig tarball missing locally; rebuilding..."
    fetch_orig_tarball "$CURRENT_VER" "V$CURRENT_VER" > /dev/null || \
        echo "  -> WARNING: orig tarball rebuild failed; continuing version check."
fi

if [ "$CURRENT_VER" = "$NEW_VER" ]; then
    echo "  -> [OK] Hatter is already on latest ($CURRENT_VER)."
    exit 0
fi

TARBALL_URL="https://github.com/$GITHUB_REPO/archive/refs/tags/$LATEST_TAG.tar.gz"
if ! curl --output /dev/null --silent --location --head --fail "$TARBALL_URL"; then
    echo "  -> [HOLD] Source archive for $LATEST_TAG is not available yet. Skipping update."
    exit 1
fi

echo "  -> [UPDATE] New version detected: $CURRENT_VER -> $NEW_VER"

NEW_SHA=$(fetch_orig_tarball "$NEW_VER" "$LATEST_TAG" | head -1)
if [ -z "$NEW_SHA" ]; then
    echo "  -> [ERROR] Could not fetch the upstream tarball; spec left untouched."
    exit 1
fi

sed -i -E "s/^Version:.*/Version:        $NEW_VER/" "$SPEC_FILE"
sed -i -E "s|^Source0:.*|Source0:        $TARBALL_URL|" "$SPEC_FILE"
sed -i -E "s|^# sha256:.*|# sha256:  $NEW_SHA|" "$SPEC_FILE"
sed -i -E "s|^%setup -q -n Hatter-.*|%setup -q -n Hatter-$NEW_VER|" "$SPEC_FILE"

sed -i -E "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: hatter-icon-theme-$NEW_VER.tar.gz|" "$DSC_FILE"

DEB_DATE=$(date -R -u)
DEB_ENTRY="hatter-icon-theme ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $NEW_VER-0\n- Update hatter-icon-theme to v$NEW_VER\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "  -> [DONE] $SPEC_FILE is ready for OBS sync."
