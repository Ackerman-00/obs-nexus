#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="localsend.spec"
CHANGES_FILE="localsend.changes"
GITHUB_REPO="localsend/localsend"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

# Get the latest version from the GitHub releases API. Using the API (not
# git ls-remote) guarantees the tag is a real release with downloadable
# assets: LocalSend sometimes pushes a bare tag (e.g. v1.18.1) that has no
# release, and ls-remote + sort -V would happily pick it up and ship a
# spec pointing at a 404 asset.
LATEST_TAG=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  "https://api.github.com/repos/$GITHUB_REPO/releases/latest" \
  | grep -oP '"tag_name":\s*"\K[^"]+')

if [ -z "$LATEST_TAG" ] || [ "$LATEST_TAG" == "null" ]; then
    echo "Error: Failed to fetch LocalSend version from GitHub. Check API limits or connection."
    exit 1
fi

# RPM spec files do not allow dashes in the Version field. Sanitize it.
LATEST_VERSION=$(echo "$LATEST_TAG" | sed 's/^v//;s@-@.@g')

# Grab the current version from the spec file
CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

# Debian_Testing recipe helper: wrap an upstream .deb into the plain-tar
# debtransform orig input. The wrapper is gitignored (*.tar) and rides the
# OBS sync; per-package actions/cache in update-packages.yml keeps it
# across fresh CI checkouts.
build_orig_wrapper() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/upstream.deb" \
        || { echo "orig .deb download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -cf "localsend-$ver.tar" -C "$tmpd" upstream.deb
    for old in localsend-*.tar; do
        [ "$old" = "localsend-$ver.tar" ] || rm -f "$old"
    done
    ls -l "localsend-$ver.tar"
    trap - EXIT
    rm -rf "$tmpd"
}

deb_url_for() {
    # deb_url_for <version>: reconstruct the upstream .deb URL (spec
    # Source0 carries a %{url} macro and a hardcoded tag).
    echo "https://github.com/$GITHUB_REPO/releases/download/v$1/LocalSend-$1-linux-x86-64.deb"
}

# Orig-tarball guard: fresh CI checkouts start without the gitignored
# wrapper (actions/cache usually restores it). Rebuild when missing so an
# OBS sync can never wipe the remote copy with nothing to re-upload.
if [ ! -f "localsend-$CURRENT_VERSION.tar" ]; then
    echo "Orig wrapper missing locally; rebuilding..."
    build_orig_wrapper "$CURRENT_VERSION" "$(deb_url_for "$CURRENT_VERSION")" || \
        echo "WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
    echo "Already up to date ($CURRENT_VERSION)."
    exit 0
fi

# Defensive check: the release asset must actually exist before we bump.
SOURCE_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/LocalSend-$LATEST_VERSION-linux-x86-64.deb"
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
sed -i -E "s|download/[^/]+/LocalSend-[^/]+\.deb|download/$LATEST_TAG/LocalSend-$LATEST_VERSION-linux-x86-64.deb|g" "$SPEC_FILE"

# 2b. Debian_Testing recipe: refresh the wrapper + keep .dsc/changelog in sync.
build_orig_wrapper "$LATEST_VERSION" "$SOURCE_URL"
DSC_FILE="localsend.dsc"
sed -i -E "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: localsend-$LATEST_VERSION.tar|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="localsend ($LATEST_VERSION-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VERSION.\n\n -- $PACKAGER  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

# 3. Update .changes
CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="* $CURRENT_DATE $PACKAGER - $LATEST_VERSION-0\n- Update localsend to v$LATEST_VERSION\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $LATEST_VERSION."
