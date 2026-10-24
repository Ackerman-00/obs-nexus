#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="koharu.spec"
CHANGES_FILE="koharu.changes"
GITHUB_REPO="koharu-rs/koharu"
PACKAGER="Ackerman-00"
# changelog heading needs an addr-spec: OBS changelog2spec
# refuses a bare name, and without it every RPM builds with an
# empty %changelog (rpmlint E: no-changelogname-tag).
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

# Get the latest version from the GitHub releases API. Using the API (not
# git ls-remote) guarantees the tag is a real release with downloadable
# assets: a bare tag with no release would point at a 404 asset.
# Koharu tags carry NO v prefix (0.83.5, not v0.83.5); sanitize only dashes
# (RPM spec files do not allow dashes in the Version field).
LATEST_TAG=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$GITHUB_REPO/releases/latest" \
  | grep -oP '"tag_name":\s*"\K[^"]+')

if [ -z "$LATEST_TAG" ] || [ "$LATEST_TAG" == "null" ]; then
    echo "Error: Failed to fetch Koharu version from GitHub. Check API limits or connection."
    exit 1
fi

LATEST_VERSION=$(echo "$LATEST_TAG" | sed 's@-@.@g')

# Grab the current version from the spec file
CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

# Debian_Testing recipe helper: wrap an upstream .deb into the gzip-compressed
# debtransform orig input (dpkg-source 3.0 (quilt) rejects an uncompressed
# .orig.tar, so the wrapper MUST stay compressed). The wrapper is gitignored
# (*.tar.gz) and rides the OBS sync.
build_orig_wrapper() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/upstream.deb" \
        || { echo "orig .deb download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -czf "koharu-$ver.tar.gz" -C "$tmpd" upstream.deb
    for old in koharu-*.tar koharu-*.tar.gz; do
        [ "$old" = "koharu-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "koharu-$ver.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
}

deb_url_for() {
    # deb_url_for <version>: reconstruct the upstream .deb URL (koharu
    # tags and asset names carry no v prefix).
    echo "https://github.com/$GITHUB_REPO/releases/download/$1/koharu_$1_amd64.deb"
}

# Orig-tarball guard: fresh checkouts start without the gitignored wrapper.
# Rebuild when missing so an OBS sync can never wipe the remote copy with
# nothing to re-upload.
if [ ! -f "koharu-$CURRENT_VERSION.tar.gz" ]; then
    echo "Orig wrapper missing locally; rebuilding..."
    build_orig_wrapper "$CURRENT_VERSION" "$(deb_url_for "$CURRENT_VERSION")" || \
        echo "WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    echo "Already up to date ($CURRENT_VERSION)."
    exit 0
fi

# Defensive check: the release asset must actually exist before we bump.
# ${LATEST_VERSION} MUST be braced: `$LATEST_VERSION_amd64` parses as the
# undefined variable $LATEST_VERSION_amd64 and expands to empty, making the
# asset URL 404 forever (latent silent-update-blocker, found 2026-10-24).
SOURCE_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/koharu_${LATEST_VERSION}_amd64.deb"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 30 "$SOURCE_URL")
if [ "$HTTP_CODE" != "200" ]; then
    echo "Release asset $SOURCE_URL returns HTTP $HTTP_CODE (not 200); not bumping to avoid a broken spec."
    echo "Staying on $CURRENT_VERSION."
    exit 0
fi

echo "Update found: $CURRENT_VERSION -> $LATEST_VERSION"

# 1. Update the Version and Release fields
sed -i -E "s/^Version:.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

# 2. Update the download URL path in the spec file with the RAW tag
sed -i -E "s|download/[^/]+/koharu_[^/]+\.deb|download/$LATEST_TAG/koharu_${LATEST_VERSION}_amd64.deb|g" "$SPEC_FILE"

# 2b. Debian_Testing recipe: refresh the wrapper + keep .dsc/changelog in sync.
build_orig_wrapper "$LATEST_VERSION" "$SOURCE_URL"
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

# 3. Update .changes
CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $LATEST_VERSION-0\n- Update koharu to $LATEST_VERSION\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $LATEST_VERSION."
