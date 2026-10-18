#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1
# update.sh for Faugus (Source Build, OBS edition)

SPEC_FILE="faugus-launcher.spec"
CHANGES_FILE="faugus-launcher.changes"
GITHUB_REPO="Faugus/faugus-launcher"
PACKAGER="Ackerman-00"
# changelog heading needs an addr-spec: OBS changelog2spec
# refuses a bare name, and without it every RPM builds with an
# empty %changelog (rpmlint E: no-changelogname-tag).
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "🔍 Checking for upstream updates on $GITHUB_REPO..."

# Faugus tags are BARE versions (2.4.4, no v prefix). The regex must accept
# ANY 3+-component version (2.5.0.1 shipped 2026-10-17): the old strict
# ^[0-9]+\.[0-9]+\.[0-9]+$ matched only 3 components, so the updater was
# structurally blind to the 4-component 2.5.0.1 and missed it for a run.
# Still excludes the historical v-prefixed / -N-suffixed tags (v1.1-24 ...).
LATEST_TAG=$(git ls-remote --tags https://github.com/$GITHUB_REPO.git 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^[0-9]+(\.[0-9]+)+$' | sort -V | tail -1)

if [ -z "$LATEST_TAG" ]; then
    echo "  -> ❌ [ERROR] Failed to fetch latest tag."
    exit 1
fi

LATEST_VERSION="$LATEST_TAG"

# Read current version from the spec file
CURRENT_VERSION=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}')

# Debian_Testing recipe helper: fetch the upstream source archive under
# its versioned orig name (content-identical rename, no recompression).
# The tarball is gitignored (*.tar.gz) and rides the OBS sync;
# per-package actions/cache in update-packages.yml keeps it across fresh
# CI checkouts.
fetch_orig_tarball() {
    local ver="$1" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 \
        "https://github.com/$GITHUB_REPO/archive/refs/tags/$ver.tar.gz" \
        -o "$tmpd/upstream.tar.gz" \
        || { echo "orig tarball download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -tzf "$tmpd/upstream.tar.gz" > /dev/null \
        || { echo "orig tarball corrupt."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    mv "$tmpd/upstream.tar.gz" "faugus-launcher-$ver.tar.gz"
    for old in faugus-launcher-*.tar.gz; do
        [ "$old" = "faugus-launcher-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "faugus-launcher-$ver.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
}

# Orig-tarball guard: fresh CI checkouts start without the gitignored
# tarball (actions/cache usually restores it). Rebuild when missing so an
# OBS sync can never wipe the remote copy with nothing to re-upload.
if [ ! -f "faugus-launcher-$CURRENT_VERSION.tar.gz" ]; then
    echo "  -> Orig tarball missing locally; rebuilding..."
    fetch_orig_tarball "$CURRENT_VERSION" || \
        echo "  -> WARNING: orig tarball rebuild failed; continuing version check."
fi

# Compare and update
if [ "$CURRENT_VERSION" != "$LATEST_VERSION" ]; then
    echo "  -> 🚀 [UPDATE] New version detected: $LATEST_VERSION (Current: $CURRENT_VERSION)"

    # Only bump once the GitHub source archive really exists
    ARCHIVE_URL="https://github.com/$GITHUB_REPO/archive/refs/tags/$LATEST_TAG.tar.gz"
    echo "  -> [CHECK] Verifying $ARCHIVE_URL"
    if ! curl --output /dev/null --silent --location --head --fail "$ARCHIVE_URL"; then
        echo "  -> ❌ [ERROR] Source archive for $LATEST_VERSION is not yet available on GitHub. Skipping update."
        exit 1
    fi

    # 1. Update the Version and Release fields
    sed -i "s/^Version:\s*.*/Version:        $LATEST_VERSION/" "$SPEC_FILE"
    sed -i "s/^Release:\s*.*/Release:        0/" "$SPEC_FILE"

    # 1b. Debian_Testing recipe: refresh the orig tarball + keep
    # .dsc/changelog in sync (archive verified 200 above).
    fetch_orig_tarball "$LATEST_VERSION"
    DSC_FILE="faugus-launcher.dsc"
    sed -i "s/^Version: .*/Version: $LATEST_VERSION/" "$DSC_FILE"
    sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: faugus-launcher-$LATEST_VERSION.tar.gz|" "$DSC_FILE"
    DEB_DATE=$(date -R -u)
    DEB_ENTRY="faugus-launcher ($LATEST_VERSION-1) unstable; urgency=medium\n\n  * New upstream release $LATEST_VERSION.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
    if [ -f "debian.changelog" ]; then
        echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
    else
        echo -e "$DEB_ENTRY" > debian.changelog
    fi

    # 2. Prepend an entry to the OBS changes file
    DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
    NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$DATE - $PACKAGER_ADDR\n\n- Update to upstream release $LATEST_VERSION\n\n"

    if [ -f "$CHANGES_FILE" ]; then
        echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
    else
        echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
    fi

    echo "  -> ✅ [DONE] $SPEC_FILE is ready for OBS sync."
else
    echo "  -> ✅ [OK] Faugus is already on latest ($CURRENT_VERSION)."
fi
