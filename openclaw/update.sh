#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="openclaw.spec"
DSC_FILE="openclaw.dsc"
CHANGES_FILE="openclaw.changes"
GITHUB_REPO="openclaw/openclaw"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

LATEST_TAG=$(git ls-remote --tags "https://github.com/$GITHUB_REPO.git" 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^v([0-9]+[.])+[0-9]+$' | sort -V | tail -1)

if [ -z "$LATEST_TAG" ]; then
    echo "Error: Failed to fetch latest tag."
    exit 1
fi

LATEST_VERSION="${LATEST_TAG#v}"
CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

echo "   Current Local: $CURRENT_VERSION"
echo "   Latest Online: $LATEST_VERSION"

DEB_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/OpenClaw-${LATEST_VERSION}-amd64.deb"

build_orig_wrapper() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    mkdir -p "$tmpd/openclaw-$ver"
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/openclaw-$ver/upstream.deb" \
        || { echo "orig .deb download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    cp openclaw-LICENSE "$tmpd/openclaw-$ver/"
    tar -czf "openclaw-$ver.tar.gz" -C "$tmpd" "openclaw-$ver"
    trap - EXIT
    rm -rf "$tmpd"
}

if [ ! -f "openclaw-$CURRENT_VERSION.tar.gz" ]; then
    echo "Orig wrapper missing locally; rebuilding..."
    build_orig_wrapper "$CURRENT_VERSION" "https://github.com/$GITHUB_REPO/releases/download/v$CURRENT_VERSION/OpenClaw-${CURRENT_VERSION}-amd64.deb" || \
        echo "WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    echo "Package is already up to date ($CURRENT_VERSION)."
    exit 0
fi

HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 60 "$DEB_URL")
if [ "$HTTP_CODE" != "200" ]; then
    echo "Release asset returns HTTP $HTTP_CODE (not 200); not bumping to avoid a broken spec."
    exit 0
fi

echo "Update found: $CURRENT_VERSION -> $LATEST_VERSION"

NEW_SHA=$(curl -fsSL --retry 3 --connect-timeout 60 "$DEB_URL" -o /tmp/openclaw-check.deb && sha256sum /tmp/openclaw-check.deb | awk '{print $1}')
if [ -z "$NEW_SHA" ]; then
    echo "Error: could not download $DEB_URL to compute its sha256; aborting bump."
    exit 1
fi

sed -i -E "s/^Version:.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"
sed -i -E "s|download/[^/]+/OpenClaw-[^/]+\\.deb|download/$LATEST_TAG/OpenClaw-${LATEST_VERSION}-amd64.deb|g" "$SPEC_FILE"
sed -i -E "s|^# sha256:.*|# sha256:  $NEW_SHA|" "$SPEC_FILE"

build_orig_wrapper "$LATEST_VERSION" "$DEB_URL" || exit 1

sed -i -E "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: openclaw-$LATEST_VERSION.tar.gz|" "$DSC_FILE"

DEB_DATE=$(date -R -u)
DEB_ENTRY="openclaw ($LATEST_VERSION-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VERSION.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $LATEST_VERSION-0\n- Update openclaw to v$LATEST_VERSION\n\n"
if [ -f "$CHANGES_FILE" ]; then
    printf "%b%s" "$NEW_CHANGELOG_ENTRY" "$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    printf "%b" "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $LATEST_VERSION."
