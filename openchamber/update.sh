#!/bin/bash
cd "$(dirname "$0")" || exit 1
. ../tools/upstream-guard.sh
curl() { command curl --connect-timeout 20 --max-time 900 "$@"; }

SPEC_FILE="openchamber.spec"
CHANGES_FILE="openchamber.changes"
GITHUB_REPO="openchamber/openchamber"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

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

X86_DEB="OpenChamber-$NEW_VER-linux-amd64.deb"

build_orig_wrapper() {
    local ver="$1"; shift
    tar -czf "openchamber-$ver.tar.gz" "$@"
    for old in openchamber-*.tar.gz; do
        [ "$old" = "openchamber-$ver.tar.gz" ] || rm -f "$old"
    done
    ls -l "openchamber-$ver.tar.gz"
}

if [ ! -f "openchamber-$CURRENT_VER.tar.gz" ]; then
    echo "Orig wrapper missing locally; rebuilding..."
    CUR_DEB="OpenChamber-$CURRENT_VER-linux-amd64.deb"
    curl -fsSL --retry 3 --connect-timeout 30 \
        "https://github.com/$GITHUB_REPO/releases/download/v$CURRENT_VER/$CUR_DEB" \
        -o "$CUR_DEB" && build_orig_wrapper "$CURRENT_VER" "$CUR_DEB" || \
        echo "WARNING: orig wrapper rebuild failed; continuing version check."
fi

if [ "$NEW_VER" == "$CURRENT_VER" ]; then
    echo "Package is already up to date."
    exit 0
fi

ASSET_NAMES=$(echo "$LATEST_JSON" | jq -r '.assets[]?.name // empty')
if ! echo "$ASSET_NAMES" | grep -qx "$X86_DEB"; then
    echo "HOLD: $LATEST_TAG has no amd64 .deb ($X86_DEB missing). Spec stays on $CURRENT_VER."
    exit 0
fi
echo "amd64 .deb asset present; proceeding."

echo "New version found! Downloading $X86_DEB for verification..."

X86_URL="https://github.com/$GITHUB_REPO/releases/download/$LATEST_TAG/$X86_DEB"
curl -fsSL --retry 3 --connect-timeout 60 "$X86_URL" -o "$X86_DEB" \
    || { echo ".deb download failed; spec left untouched."; exit 1; }
if ! [ -s "$X86_DEB" ]; then
    echo "$X86_DEB is empty; spec left untouched."
    rm -f "$X86_DEB"
    exit 1
fi

DEB_TMP=$(mktemp -d)
( ar x "$X86_DEB" --output "$DEB_TMP" >/dev/null 2>&1 || rm -rf "$DEB_TMP" ) || \
    { echo ".deb is not an ar archive; spec left untouched."; rm -f "$X86_DEB"; exit 1; }
if [ ! -s "$DEB_TMP/data.tar.xz" ] && [ ! -s "$DEB_TMP/data.tar.zst" ] && [ ! -s "$DEB_TMP/data.tar.gz" ]; then
    echo ".deb has no data.tar member; spec left untouched."; rm -rf "$DEB_TMP" "$X86_DEB"; exit 1
fi
if [ ! -s "$DEB_TMP/control.tar.xz" ] && [ ! -s "$DEB_TMP/control.tar.zst" ] && [ ! -s "$DEB_TMP/control.tar.gz" ]; then
    echo ".deb has no control.tar member; spec left untouched."; rm -rf "$DEB_TMP" "$X86_DEB"; exit 1
fi
PAYLOAD_TMP=$(mktemp -d)
if [ -s "$DEB_TMP/data.tar.xz" ]; then tar -xpf "$DEB_TMP/data.tar.xz" -C "$PAYLOAD_TMP"; \
elif [ -s "$DEB_TMP/data.tar.zst" ]; then tar --zstd -xpf "$DEB_TMP/data.tar.zst" -C "$PAYLOAD_TMP"; \
else tar -xzf "$DEB_TMP/data.tar.gz" -C "$PAYLOAD_TMP"; fi
[ -x "$PAYLOAD_TMP/opt/OpenChamber/openchamber" ] || \
    { echo "Binary missing from .deb payload (expected opt/OpenChamber/openchamber); spec left untouched."; rm -rf "$DEB_TMP" "$PAYLOAD_TMP" "$X86_DEB"; exit 1; }
[ -f "$PAYLOAD_TMP/usr/share/applications/openchamber.desktop" ] || \
    { echo "Desktop file missing from .deb payload; spec left untouched."; rm -rf "$DEB_TMP" "$PAYLOAD_TMP" "$X86_DEB"; exit 1; }
[ -f "$PAYLOAD_TMP/usr/share/icons/hicolor/512x512/apps/openchamber.png" ] || \
    { echo "Icon missing from .deb payload; spec left untouched."; rm -rf "$DEB_TMP" "$PAYLOAD_TMP" "$X86_DEB"; exit 1; }
rm -rf "$DEB_TMP" "$PAYLOAD_TMP"

echo "All guards passed; updating $SPEC_FILE..."
sed -i "s|^Version:.*|Version:        $NEW_VER|" "$SPEC_FILE"
sed -i "s|^Release:.*|Release:        0|" "$SPEC_FILE"

build_orig_wrapper "$NEW_VER" "$X86_DEB"
DSC_FILE="openchamber.dsc"
sed -i "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
sed -i "s|^Debtransform-Tar:.*|Debtransform-Tar: openchamber-$NEW_VER.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="openchamber ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream release $NEW_VER.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

echo "Updating changelog ($CHANGES_FILE)..."
CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $NEW_VER-$(spec_release "$SPEC_FILE")\n- Update openchamber to v$NEW_VER\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! OpenChamber updated to v$NEW_VER. Ready for OBS sync."
