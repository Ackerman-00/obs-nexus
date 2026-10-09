#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="opencode-desktop.spec"
CHANGES_FILE="opencode-desktop.changes"
GITHUB_REPO="anomalyco/opencode"
# Canonical upstream for v2 desktop builds: the stable channel 302-redirects
# to https://opencode.ai/files/bin/<ver>/opencode-desktop-linux-amd64.deb
# (GitHub tags carry no desktop DEB asset). The versioned files/bin URL below
# floats with %{version}; only the stable endpoint is queried for discovery.
STABLE_URL="https://opencode.ai/download/stable/linux-x64-deb"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"
DSC_FILE="opencode-desktop.dsc"
DEB_CHANGELOG="debian.changelog"

# build_orig_tarball <version> <deb-url>: wrap the whole upstream .deb
# into a plain-tar debtransform orig input (no parsing, no recompression),
# dropping tarballs for any other version. The tarball is gitignored and
# rides the OBS sync; it is the DEBTRANSFORM-TAR input debtransform needs
# at build time.
build_orig_tarball() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --retry-all-errors -L --max-time 900 "$url" -o "$tmpd/upstream.deb" \
        || { echo "orig .deb download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -cf "opencode-desktop-$ver.tar" -C "$tmpd" upstream.deb
    for old in opencode-desktop-*.tar; do
        [ "$old" = "opencode-desktop-$ver.tar" ] || rm -f "$old"
    done
    # Drop any tarballs from the previous member-copy scheme.
    rm -f opencode-desktop-*.tar.xz
    ls -l "opencode-desktop-$ver.tar"
    trap - EXIT
    rm -rf "$tmpd"
}

echo "Checking for upstream updates on $GITHUB_REPO..."

CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

# Orig-tarball guard: fresh CI checkouts start without the gitignored tarball
# (actions/cache usually restores it). If it is missing, an OBS sync
# triggered by any tracked-file drift would wipe the remote copy with
# nothing to re-upload and break the Debian_Testing build -- so rebuild it
# from the (unchanged) upstream .deb before doing anything else.
if [ ! -f "opencode-desktop-$CURRENT_VERSION.tar" ]; then
    echo "Orig tarball missing locally; rebuilding from upstream .deb..."
    build_orig_tarball "$CURRENT_VERSION" "https://opencode.ai/files/bin/$CURRENT_VERSION/opencode-desktop-linux-amd64.deb" || \
        echo "WARNING: orig tarball rebuild failed; continuing version check anyway."
fi

# Primary: parse the version out of the stable channel's redirect target.
# Retries ride out CDN transients: a false "unreachable" strands the package
# on the GitHub fallback, which can never see v2 desktop builds.
STABLE_VER=""
REDIRECT=$(curl -sIL --retry 3 --retry-all-errors --retry-delay 5 --max-time 30 "$STABLE_URL" | grep -i '^location:' | tail -1 | tr -d '\r')
if [ -n "$REDIRECT" ]; then
    STABLE_VER=$(echo "$REDIRECT" | grep -oP 'files/bin/\K[0-9][^/]*' | head -1)
fi

LATEST_VERSION=""
if [ -n "$STABLE_VER" ] && [ "$STABLE_VER" != "$CURRENT_VERSION" ]; then
    SOURCE_URL="https://opencode.ai/files/bin/$STABLE_VER/opencode-desktop-linux-amd64.deb"
    HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -L --retry 2 --retry-all-errors --max-time 30 "$SOURCE_URL")
    if [ "$HTTP_CODE" = "200" ]; then
        LATEST_VERSION="$STABLE_VER"
    else
        echo "Stable channel points at $STABLE_VER but the asset returns HTTP $HTTP_CODE; falling back to GitHub tags..."
    fi
elif [ -n "$STABLE_VER" ]; then
    echo "Package is already at $CURRENT_VERSION (stable channel). No update needed."
    exit 0
else
    echo "Stable channel unreachable; falling back to GitHub tags..."
fi

if [ -z "$LATEST_VERSION" ]; then
# Fallback: candidate tags newest-first. Upstream sometimes pushes bare tags (e.g. the
# v2.0.x series, which have no GitHub release object and no desktop DEB
# asset). Walk down until a tag whose desktop DEB asset actually exists, so a
# stray asset-less tag can never pin us stale or ship a 404 spec.
ALL_TAGS=$(git ls-remote --tags https://github.com/$GITHUB_REPO.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^v?[0-9]' | sort -uV -r)

if [ -z "$ALL_TAGS" ]; then
    echo "Error: Failed to fetch tags."
    exit 1
fi

for TAG in $ALL_TAGS; do
    CANDIDATE=$(echo "$TAG" | sed 's/^v//')
    if [ "$CANDIDATE" = "$CURRENT_VERSION" ]; then
        echo "Package is already at $CANDIDATE. No update needed."
        exit 0
    fi
    SOURCE_URL="https://github.com/$GITHUB_REPO/releases/download/v$CANDIDATE/opencode-desktop-linux-amd64.deb"
    HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 30 "$SOURCE_URL")
    if [ "$HTTP_CODE" = "200" ]; then
        LATEST_VERSION="$CANDIDATE"
        break
    fi
    echo "Tag v$CANDIDATE has no desktop DEB asset (HTTP $HTTP_CODE); trying older tag..."
done
fi

if [ -z "$LATEST_VERSION" ]; then
    echo "No newer tag with a desktop DEB asset found; staying on $CURRENT_VERSION."
    exit 0
fi

echo "Update found: $CURRENT_VERSION -> $LATEST_VERSION"

# Defensive check: the DEB asset must actually exist before we bump (already
# proven 200 above; re-verify cheaply to close any TOCTOU gap). Prefer the
# canonical files/bin location (stable-channel builds); fall back to GitHub.
SOURCE_URL="https://opencode.ai/files/bin/$LATEST_VERSION/opencode-desktop-linux-amd64.deb"
HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 30 "$SOURCE_URL")
if [ "$HTTP_CODE" != "200" ]; then
    SOURCE_URL="https://github.com/$GITHUB_REPO/releases/download/v$LATEST_VERSION/opencode-desktop-linux-amd64.deb"
    HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 30 "$SOURCE_URL")
fi
if [ "$HTTP_CODE" != "200" ]; then
    echo "Release asset for $LATEST_VERSION returns HTTP $HTTP_CODE (not 200); not bumping to avoid a broken spec."
    echo "Staying on $CURRENT_VERSION."
    exit 0
fi

sed -i "s/^Version:.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
sed -i "s/^Release:.*/Release:        0/" "$SPEC_FILE"

# Debian_Testing recipe (opencode-desktop.dsc + flat debian.* files, built
# server-side via debtransform at build time): keep the .dsc Version and
# Debtransform-Tar in sync, prepend a debian/changelog entry, and refresh
# the orig wrapper tar holding the whole upstream .deb (no parsing, no
# recompression). The tarball is gitignored (*.tar) and rides the OBS sync
# like any other top-level package file; actions/cache in update-packages.yml
# keeps it across fresh CI checkouts so this 218MB download only happens on
# real version changes.
sed -i "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: opencode-desktop-$LATEST_VERSION.tar|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="opencode-desktop ($LATEST_VERSION-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VERSION (stable channel repack).\n\n -- $PACKAGER  $DEB_DATE\n\n"
if [ -f "$DEB_CHANGELOG" ]; then
    echo -e "${DEB_ENTRY}$(cat $DEB_CHANGELOG)" > "$DEB_CHANGELOG"
else
    echo -e "$DEB_ENTRY" > "$DEB_CHANGELOG"
fi
build_orig_tarball "$LATEST_VERSION" "$SOURCE_URL"

CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="* $CURRENT_DATE $PACKAGER - $LATEST_VERSION-0\n- Update opencode-desktop to v$LATEST_VERSION\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Successfully updated to $LATEST_VERSION."
