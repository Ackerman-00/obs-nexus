#!/bin/bash
cd "$(dirname "$0")" || exit 1
curl() { command curl --connect-timeout 20 --max-time 900 "$@"; }

SPEC_FILE="mixtapes.spec"
CHANGES_FILE="mixtapes.changes"
DSC_FILE="mixtapes.dsc"
GITHUB_REPO="m-obeid/Mixtapes"
V8_ARCHIVE="librusty_v8_release_x86_64-unknown-linux-gnu.a.gz"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

if [ -n "$GITHUB_TOKEN" ]; then
    API_RESPONSE=$(curl -sL -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/commits/main")
else
    API_RESPONSE=$(curl -sL "https://api.github.com/repos/$GITHUB_REPO/commits/main")
fi

LATEST_COMMIT=$(echo "$API_RESPONSE" | jq -r '.sha')
LATEST_DATE_RAW=$(echo "$API_RESPONSE" | jq -r '.commit.committer.date')

if [ -z "$LATEST_COMMIT" ] || [ "$LATEST_COMMIT" == "null" ]; then
    echo "Error: Failed to fetch main commit from GitHub."
    exit 1
fi

SHORT_COMMIT=${LATEST_COMMIT:0:7}
GITDATE=$(echo "$LATEST_DATE_RAW" | sed 's/[-T:Z]//g')
CURRENT_COMMIT=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')

if [ "$CURRENT_COMMIT" == "$LATEST_COMMIT" ]; then
    echo "Package is already at the latest commit ($SHORT_COMMIT). No update needed."
    exit 0
fi

echo "New commit: ${CURRENT_COMMIT:0:7} -> $SHORT_COMMIT"

TARBALL="mixtapes-$SHORT_COMMIT.tar.gz"
TMPD=$(mktemp -d)
trap 'rm -rf "$TMPD"' EXIT

curl -fsSL --retry 3 --connect-timeout 30 "https://github.com/$GITHUB_REPO/archive/$LATEST_COMMIT.tar.gz" -o "$TMPD/src.tar.gz" \
    || { echo "Source download failed; spec left untouched."; exit 1; }
tar -xzf "$TMPD/src.tar.gz" -C "$TMPD" \
    || { echo "Source tarball corrupt; spec left untouched."; exit 1; }
TOPD=$(tar -tzf "$TMPD/src.tar.gz" | head -1 | cut -d/ -f1)
[ -n "$TOPD" ] && [ -d "$TMPD/$TOPD" ] \
    || { echo "Unexpected source layout; spec left untouched."; exit 1; }

echo "Vendoring cargo dependencies so the build works offline..."
(
    cd "$TMPD/$TOPD" || exit 1
    cargo vendor --locked vendor-crates > "$TMPD/vendor_config.raw" 2> "$TMPD/vendor.err" || exit 1
    mkdir -p .cargo
    if head -1 "$TMPD/vendor_config.raw" | grep -q "^\[source"; then
        cp "$TMPD/vendor_config.raw" .cargo/config.toml
    else
        sed -n '/^\[source/,$p' "$TMPD/vendor_config.raw" > .cargo/config.toml
    fi
) || { cat "$TMPD/vendor.err"; echo "cargo vendor failed; spec left untouched."; exit 1; }
[ -d "$TMPD/$TOPD/vendor-crates" ] && [ -s "$TMPD/$TOPD/.cargo/config.toml" ] \
    || { echo "Vendored tree incomplete; spec left untouched."; exit 1; }

V8_VERSION=$(awk '/^name = "v8"$/{f=1} f&&/^version = /{gsub(/"/,"",$3); print $3; exit}' "$TMPD/$TOPD/Cargo.lock")
[ -n "$V8_VERSION" ] \
    || { echo "Cannot determine the v8 crate version; spec left untouched."; exit 1; }
echo "Fetching prebuilt V8 static library for the v8 crate $V8_VERSION..."
curl -fsSL --retry 3 --connect-timeout 30 \
    "https://github.com/denoland/rusty_v8/releases/download/v${V8_VERSION}/${V8_ARCHIVE}" \
    -o "$TMPD/$TOPD/$V8_ARCHIVE" \
    || { echo "V8 archive download failed; spec left untouched."; exit 1; }
[ "$(head -c 2 "$TMPD/$TOPD/$V8_ARCHIVE")" = "$(printf '\037\213')" ] \
    || { echo "V8 archive is not gzip data; spec left untouched."; exit 1; }
V8_SHA=$(sha256sum "$TMPD/$TOPD/$V8_ARCHIVE" | awk '{print $1}')

BASE_VERSION=$(grep -oP '(?<=<release version=")[^"]+' "$TMPD/$TOPD/com.pocuguy.Muse.metainfo.xml" 2>/dev/null | head -1 | tr '-' '.' | tr -cd '0-9.')
[ -n "$BASE_VERSION" ] \
    || { echo "Cannot determine upstream release version; spec left untouched."; exit 1; }

rm -f mixtapes-*.tar.gz
tar -czf "$TARBALL" -C "$TMPD" "$TOPD"
[ -s "$TARBALL" ] \
    || { echo "Packed tarball is empty; spec left untouched."; exit 1; }

sed -i -E "s/^%global commit.*/%global commit          $LATEST_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global shortcommit.*/%global shortcommit     $SHORT_COMMIT/" "$SPEC_FILE"
sed -i -E "s/^%global gitdate.*/%global gitdate         $GITDATE/" "$SPEC_FILE"
sed -i -E "s/^%global base_version.*/%global base_version    $BASE_VERSION/" "$SPEC_FILE"
sed -i -E "s/^Version:.*/Version:        %{base_version}+git%{gitdate}.%{shortcommit}/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"
awk -v h="$V8_SHA" '/^%global v8_archive/{print; d=1; next} d==1 && /^# sha256: /{print "# sha256: " h; d=0; next} {print}' \
    "$SPEC_FILE" > "$SPEC_FILE.tmp" && mv "$SPEC_FILE.tmp" "$SPEC_FILE"

DSC_VER="${BASE_VERSION}+git${GITDATE}.${SHORT_COMMIT}"
sed -i -E "s/^Version: .*/Version: ${DSC_VER}/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: mixtapes-${SHORT_COMMIT}.tar.gz|" "$DSC_FILE"

DEB_DATE=$(date -R -u)
DEB_ENTRY="mixtapes (${DSC_VER}-1) unstable; urgency=medium\n\n  * New upstream snapshot $SHORT_COMMIT.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "${DEB_ENTRY}" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version ${DSC_VER}-0\n- Update mixtapes to upstream main $SHORT_COMMIT\n\n"
if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! mixtapes at $SHORT_COMMIT (upstream release $BASE_VERSION, v8 $V8_VERSION). Ready for OBS sync."
