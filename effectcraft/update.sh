#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="effectcraft.spec"
CHANGES_FILE="effectcraft.changes"
GITHUB_REPO="storytold/effectcraft"
PACKAGER="Ackerman-00"

# Upstream layout: release tag v<ver>, native per-distro artifacts
# <name>-<ver>-linux-x86_64.{rpm,deb}. The RPM is repacked for
# Tumbleweed, the DEB for Debian_Testing; both get our own
# distro-correct dependency mapping (upstream's RPM carries Fedora
# names).
echo "Checking for upstream updates on $GITHUB_REPO..."

# Get latest release data (authenticated to avoid rate limits).
# Retry on transient network/API failures so one hiccup does not stub the
# version and abort the whole update.
LATEST_TAG=""
LATEST_JSON=""
for attempt in 1 2 3; do
    if [ -n "$GITHUB_TOKEN" ]; then
        RESP=$(curl -s --retry 3 --connect-timeout 15 -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/releases/latest")
    else
        RESP=$(curl -s --retry 3 --connect-timeout 15 "https://api.github.com/repos/$GITHUB_REPO/releases/latest")
    fi
    LATEST_TAG=$(echo "$RESP" | jq -r '.tag_name')
    if [ -n "$LATEST_TAG" ] && [ "$LATEST_TAG" != "null" ]; then
        LATEST_JSON="$RESP"
        break
    fi
    echo "   Retry $attempt: could not fetch latest tag from GitHub..."
    sleep 5
done
NEW_VER="${LATEST_TAG#v}"

if [ -z "$NEW_VER" ] || [ "$NEW_VER" == "null" ]; then
    echo "Error: Could not fetch latest version."
    exit 1
fi

CURRENT_VER=$(grep "^Version:" "$SPEC_FILE" | awk '{print $2}')

echo "   Current Local: $CURRENT_VER"
echo "   Latest Online: $NEW_VER"

RPM_NAME="effectcraft-$NEW_VER-linux-x86_64.rpm"
DEB_NAME="effectcraft-$NEW_VER-linux-x86_64.deb"

# Debian_Testing recipe helper: wrap the upstream .deb into the gzip-compressed
# debtransform orig input. The wrapper is gitignored (*.tar.gz) and rides the
# OBS sync; per-package actions/cache in update-packages.yml keeps it
# across fresh CI checkouts. (The RPM side needs nothing local: Source0 is
# a versioned URL fetched server-side by download_files.)
build_orig_wrapper() {
    local ver="$1" url="$2" tmpd
    tmpd=$(mktemp -d)
    trap 'rm -rf "$tmpd"' EXIT
    curl -fsSL --retry 3 --connect-timeout 30 "$url" -o "$tmpd/upstream.deb" \
        || { echo "orig .deb download failed."; trap - EXIT; rm -rf "$tmpd"; return 1; }
    tar -czf "effectcraft-$ver.tar.gz" -C "$tmpd" upstream.deb
    for old in effectcraft-*.tar.gz; do
        [ "$old" = "effectcraft-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "effectcraft-$ver.tar.gz"
    trap - EXIT
    rm -rf "$tmpd"
}

deb_url_for() {
    echo "https://github.com/$GITHUB_REPO/releases/download/v$1/effectcraft-$1-linux-x86_64.deb"
}

# Orig-tarball guard: fresh CI checkouts start without the gitignored
# wrapper (actions/cache usually restores it). Rebuild when missing so an
# OBS sync can never wipe the remote copy with nothing to re-upload.
if [ ! -f "effectcraft-$CURRENT_VER.tar.gz" ]; then
    echo "Orig wrapper missing locally; rebuilding..."
    build_orig_wrapper "$CURRENT_VER" "$(deb_url_for "$CURRENT_VER")" || \
        echo "WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$NEW_VER" == "$CURRENT_VER" ]; then
    echo "Package is already up to date."
    exit 0
fi

# Asset guard: only bump once BOTH native artifacts really exist (a tag
# can exist before its assets finish uploading; a blind bump ships 404s).
ASSET_NAMES=$(echo "$LATEST_JSON" | jq -r '.assets[]?.name // empty')
for want in "$RPM_NAME" "$DEB_NAME"; do
    if ! echo "$ASSET_NAMES" | grep -qx "$want"; then
        echo "HOLD: $LATEST_TAG has no $want asset. Spec stays on $CURRENT_VER."
        exit 0
    fi
done
echo "RPM + DEB assets present; proceeding."
# Payload reconciliation guard (2026-10-10: pdfcraft 0.5.0 shipped a new
# NOTICE + usr/share/pdfcraft/models dir that spec %files / debian.rules
# did not cover -> TW "Installed (but unpackaged) file(s)" failure).
# Runs BEFORE any mutation: the NEW .deb payload (presence verified by
# the asset guard above) must be fully covered by spec %files, with
# %install + debian.rules copies for any new data dir, and the .changes
# order must stay descending. A HOLD leaves the tree untouched.
echo "Reconciling new payload against spec..."
RECON_TMP=$(mktemp -d)
RECON_TOOL="$(pwd)/../tools/reconcile-payload.py"
if [ ! -f "$RECON_TOOL" ]; then
    echo "HOLD: reconcile tool missing ($RECON_TOOL). Spec stays on $CURRENT_VER."
    rm -rf "$RECON_TMP"
    exit 0
fi
if ! curl -fsSL --retry 3 --connect-timeout 30 \
        "$(deb_url_for "$NEW_VER")" -o "$RECON_TMP/new.deb"; then
    echo "HOLD: new .deb download failed; cannot reconcile. Spec stays on $CURRENT_VER."
    rm -rf "$RECON_TMP"
    exit 0
fi
if ! python3 "$RECON_TOOL" "effectcraft" "$RECON_TMP/new.deb" "$SPEC_FILE" "$CHANGES_FILE" "debian.rules"; then
    echo "HOLD: payload/spec drift above. Spec stays on $CURRENT_VER."
    rm -rf "$RECON_TMP"
    exit 0
fi
rm -rf "$RECON_TMP"

echo "New version found! Updating $SPEC_FILE..."
sed -i "s|^Version:.*|Version:        $NEW_VER|" "$SPEC_FILE"
sed -i "s|^Release:.*|Release:        0|" "$SPEC_FILE"
sed -i "s|^Source0:.*|Source0:        https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/$RPM_NAME|" "$SPEC_FILE"

# Debian_Testing recipe: refresh the wrapper + keep .dsc/changelog in sync
# (asset URLs verified present via the asset guard above).
build_orig_wrapper "$NEW_VER" "$(deb_url_for "$NEW_VER")"
DSC_FILE="effectcraft.dsc"
sed -i "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: effectcraft-$NEW_VER.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="effectcraft ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- $PACKAGER  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

echo "Updating changelog ($CHANGES_FILE)..."
CURRENT_DATE=$(LC_ALL=C date +"%a %b %d %Y")
NEW_CHANGELOG_ENTRY="* $CURRENT_DATE $PACKAGER - $NEW_VER-0\n- Update effectcraft to v$NEW_VER\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! EffectCraft updated to v$NEW_VER. Ready for OBS sync."
