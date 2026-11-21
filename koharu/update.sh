#!/bin/bash
SELF_DIR=$(cd "$(dirname "$0")" && pwd) || exit 1
. "$SELF_DIR/../tools/upstream-guard.sh"
cd "$SELF_DIR" || exit 1
curl() { command curl --connect-timeout 20 --max-time 900 "$@"; }

SPEC_FILE="koharu.spec"
CHANGES_FILE="koharu.changes"
GITHUB_REPO="koharu-rs/koharu"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

LATEST_TAG=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$GITHUB_REPO/releases/latest" \
  | grep -oP '"tag_name":\s*"\K[^"]+')

if [ -z "$LATEST_TAG" ] || [ "$LATEST_TAG" == "null" ]; then
    echo "Error: Failed to fetch Koharu version from GitHub. Check API limits or connection."
    exit 1
fi

LATEST_VERSION=$(echo "$LATEST_TAG" | sed 's@-@.@g')

CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

build_orig_wrapper() {
    local ver="$1" url="$2" want="${3:-}" tmpd got
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/upstream.deb" \
        || { echo "orig .deb download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    got=$(sha256sum "$tmpd/upstream.deb" | awk '{print $1}')
    if [ -n "$want" ] && [ "$want" != "repin" ] && [ "$got" != "$want" ]; then
        echo "checksum mismatch: expected $want, download is $got"
        trap - EXIT; rm -rf "$tmpd"; return 1
    fi
    tar -czf "koharu-$ver.tar.gz" -C "$tmpd" upstream.deb
    for old in koharu-*.tar koharu-*.tar.gz; do
        [ "$old" = "koharu-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "koharu-$ver.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
    echo "SHA256=$got"
}

spec_sha() {
    grep -E '^# sha256:' "$SPEC_FILE" | head -1 | awk '{print $NF}'
}

deb_url_for() {
    echo "https://github.com/$GITHUB_REPO/releases/download/$1/koharu_$1_amd64.deb"
}

if [ ! -f "koharu-$CURRENT_VERSION.tar.gz" ]; then
    echo "Orig wrapper missing locally; rebuilding..."
    build_orig_wrapper "$CURRENT_VERSION" "$(deb_url_for "$CURRENT_VERSION")" "$(spec_sha)" || \
        echo "WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    echo "Already up to date ($CURRENT_VERSION)."
    exit 0
fi

SOURCE_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/koharu_${LATEST_VERSION}_amd64.deb"
if ! asset_http_ok "$SOURCE_URL"; then
    echo "Release asset $SOURCE_URL returns HTTP $ASSET_HTTP_CODE; not bumping to avoid a broken spec."
    echo "Staying on $CURRENT_VERSION."
    exit 0
fi

echo "Update found: $CURRENT_VERSION -> $LATEST_VERSION"

sed -i -E "s/^Version:.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

sed -i -E "s|download/[^/]+/koharu_[^/]+\.deb|download/$LATEST_TAG/koharu_${LATEST_VERSION}_amd64.deb|g" "$SPEC_FILE"

BUILD_OUT=$(build_orig_wrapper "$LATEST_VERSION" "$SOURCE_URL" "repin") || { echo "orig wrapper build failed; not bumping."; exit 1; }
printf '%s\n' "$BUILD_OUT"
NEW_SHA=$(printf '%s\n' "$BUILD_OUT" | sed -n 's/^SHA256=//p' | tail -1)
[ -n "$NEW_SHA" ] || { echo "could not read the new sha256; not bumping."; exit 1; }
grep -q '^# sha256:' "$SPEC_FILE" && sed -i -E "s|^# sha256:.*|# sha256:  $NEW_SHA|" "$SPEC_FILE" || sed -i -E "/^Version:/a # sha256:  $NEW_SHA" "$SPEC_FILE"
DSC_FILE="koharu.dsc"
sed -i -E "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: koharu-$LATEST_VERSION.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="koharu ($LATEST_VERSION-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VERSION.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $LATEST_VERSION-0\n- Update koharu to $LATEST_VERSION\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $LATEST_VERSION."
