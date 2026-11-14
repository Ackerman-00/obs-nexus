#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="openclaw.spec"
DSC_FILE="openclaw.dsc"
CHANGES_FILE="openclaw.changes"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"
MANIFEST_URL="https://github.com/openclaw/openclaw/releases/latest/download/latest.json"

echo "Checking for upstream companion-app updates..."

LATEST_JSON=$(curl -fsSL -m 60 "$MANIFEST_URL") || {
    echo "Error: failed to fetch $MANIFEST_URL" >&2
    exit 1
}

read LATEST_VERSION LATEST_SHA < <(python3 -c "
import json, sys
d = json.loads(sys.argv[1])
v = d['version']
sha = next((a['sha256'] for a in d.get('linuxPublication', {}).get('assets', []) if a['name'] == f'OpenClaw-{v}-amd64.deb'), '')
print(v, sha)
" "$LATEST_JSON")

if [ -z "$LATEST_VERSION" ] || [ -z "$LATEST_SHA" ]; then
    echo "Error: no linux x86_64 .deb asset in the latest companion manifest (version=$LATEST_VERSION sha=$LATEST_SHA)." >&2
    echo "Upstream likely shipped a macOS-only release; keeping the current pin." >&2
    exit 1
fi

CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

echo "   Current Local: $CURRENT_VERSION"
echo "   Latest Online: $LATEST_VERSION"

DEB_URL="https://github.com/openclaw/openclaw/releases/download/v$LATEST_VERSION/OpenClaw-$LATEST_VERSION-amd64.deb"

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
    build_orig_wrapper "$CURRENT_VERSION" "https://github.com/openclaw/openclaw/releases/download/v$CURRENT_VERSION/OpenClaw-${CURRENT_VERSION}-amd64.deb" || \
        echo "WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    CURRENT_SHA=$(grep -E "^# sha256:" "$SPEC_FILE" | head -1 | awk '{print $3}')
    if [ "$CURRENT_SHA" != "$LATEST_SHA" ]; then
        echo "Upstream respinned $LATEST_VERSION (sha256 $CURRENT_SHA -> $LATEST_SHA); re-pinning."
        sed -i -E "s|^# sha256:.*|# sha256:  $LATEST_SHA|" "$SPEC_FILE"
    else
        echo "Package is already up to date ($CURRENT_VERSION)."
    fi
    exit 0
fi

HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -I -L --max-time 60 "$DEB_URL")
if [ "$HTTP_CODE" != "200" ]; then
    echo "Release asset returns HTTP $HTTP_CODE (not 200); not bumping to avoid a broken spec."
    exit 0
fi

echo "Update found: $CURRENT_VERSION -> $LATEST_VERSION"

sed -i -E "s/^Version:.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"
sed -i -E "s|^# sha256:.*|# sha256:  $LATEST_SHA|" "$SPEC_FILE"

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
