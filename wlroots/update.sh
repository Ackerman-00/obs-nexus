#!/bin/bash
# Always operate in this script's own directory (the workflow pushds here,
# but a direct `bash <pkg>/update.sh` from the repo root would otherwise
# touch the wrong files).
cd "$(dirname "$0")" || exit 1

SPEC_FILE="wlroots.spec"
CHANGES_FILE="wlroots.changes"
PACKAGER="Ackerman-00 <quietcraft@gmail.com>"

echo "Checking for upstream wlroots releases..."

LATEST_TAG=$(curl -s "https://gitlab.freedesktop.org/api/v4/projects/wlroots%2Fwlroots/releases?per_page=1" | jq -r '.[0].tag_name')

if [ -z "$LATEST_TAG" ] || [ "$LATEST_TAG" == "null" ]; then
    echo "Error: Failed to fetch wlroots latest release from GitLab."
    exit 1
fi

# wlroots tags look like "0.20.2" (no 'v' prefix)
NEW_VER="$LATEST_TAG"
NEW_SUFFIX="${NEW_VER%.*}"          # 0.20
NEW_PATCH="${NEW_VER##*.}"          # 2
NEW_SOVER="${NEW_SUFFIX//./_}"      # 0_20

CURRENT_VER=$(grep -E "^Version:" "$SPEC_FILE" | awk '{print $2}' | sed 's/%{ver_suffix}\.%{patch_ver}//')
CURRENT_SUFFIX=$(grep -E "^%global ver_suffix" "$SPEC_FILE" | awk '{print $3}')
CURRENT_PATCH=$(grep -E "^%global patch_ver" "$SPEC_FILE" | awk '{print $3}')

echo "   Current local: $CURRENT_SUFFIX.$CURRENT_PATCH"
echo "   Latest online: $NEW_VER"

if [ "$CURRENT_SUFFIX.$CURRENT_PATCH" == "$NEW_VER" ]; then
    echo "Package is already up to date."
    exit 0
fi

echo "Update found: $CURRENT_SUFFIX.$CURRENT_PATCH -> $NEW_VER"

sed -i -E "s/^%global ver_suffix.*/%global ver_suffix $NEW_SUFFIX/" "$SPEC_FILE"
sed -i -E "s/^%global sover.*/%global sover      $NEW_SOVER/" "$SPEC_FILE"
sed -i -E "s/^%global patch_ver.*/%global patch_ver  $NEW_PATCH/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

FORMATTED_DATE=$(LC_ALL=C date +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$FORMATTED_DATE - $PACKAGER\n\n- Update wlroots to $NEW_VER\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! wlroots updated to $NEW_VER. Ready for OBS sync."
