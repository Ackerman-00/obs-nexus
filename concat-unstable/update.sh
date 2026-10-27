#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="concat-unstable.spec"
CHANGES_FILE="concat-unstable.changes"
GITHUB_REPO="jub0t/concat"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"
FFMPEG_RELEASE="https://github.com/BtbN/FFmpeg-Builds/releases/download/latest"
FFMPEG_VERSION="8.1"
FFMPEG_FILE="ffmpeg-n8.1-latest-linux64-gpl-shared-8.1.tar.xz"
ORT_VERSION="1.28.0"
ORT_TGZ="onnxruntime-linux-x64-$ORT_VERSION.tgz"

echo "Checking for upstream updates on $GITHUB_REPO main..."

HEAD_SHA=""
HEAD_DATE_RAW=""
for attempt in 1 2 3; do
    if [ -n "$GITHUB_TOKEN" ]; then
        RESP=$(curl -s --retry 3 --connect-timeout 15 -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/commits/main")
    else
        RESP=$(curl -s --retry 3 --connect-timeout 15 "https://api.github.com/repos/$GITHUB_REPO/commits/main")
    fi
    HEAD_SHA=$(echo "$RESP" | jq -r '.sha')
    HEAD_DATE_RAW=$(echo "$RESP" | jq -r '.commit.committer.date')
    if [ -n "$HEAD_SHA" ] && [ "$HEAD_SHA" != "null" ]; then
        break
    fi
    echo "   Retry $attempt: could not fetch main HEAD..."
    sleep 5
done

if [ -z "$HEAD_SHA" ] || [ "$HEAD_SHA" == "null" ]; then
    echo "Error: Failed to fetch main HEAD."
    exit 1
fi

LATEST_TAG=$(git ls-remote --tags "https://github.com/$GITHUB_REPO.git" 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' | sort -V | tail -1)
BASE_VER="${LATEST_TAG#v}"
if [ -z "$BASE_VER" ]; then
    echo "Error: Failed to resolve base release tag."
    exit 1
fi

SHORT=${HEAD_SHA:0:7}
GITDATE=$(echo "$HEAD_DATE_RAW" | sed 's/[-T:Z]//g')
CURRENT_COMMIT=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')
CURRENT_PIN=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')
TARBALL="concat-unstable-$BASE_VER+git$GITDATE.$SHORT.tar.gz"

if [ "$CURRENT_COMMIT" = "$HEAD_SHA" ]; then
    echo "Package is already at main $SHORT (base $BASE_VER). No update needed."
    exit 0
fi

echo "Building snapshot: base $BASE_VER + main $SHORT ($HEAD_DATE_RAW)"
TMPD=$(mktemp -d)
trap 'rm -rf "$TMPD"' EXIT

curl -fsSL --retry 3 --connect-timeout 30 "https://github.com/$GITHUB_REPO/archive/$HEAD_SHA.tar.gz" -o "$TMPD/main.tar.gz" \
    || { echo "Source download failed; spec left untouched."; exit 1; }
tar -xzf "$TMPD/main.tar.gz" -C "$TMPD" \
    || { echo "Source tarball corrupt; spec left untouched."; exit 1; }
TOPD=$(tar -tzf "$TMPD/main.tar.gz" | head -1 | cut -d/ -f1)
if [ "$TOPD" != "concat-$HEAD_SHA" ]; then
    echo "Note: archive top dir is $TOPD, normalizing to concat-$HEAD_SHA."
    mv "$TMPD/$TOPD" "$TMPD/concat-$HEAD_SHA" \
        || { echo "Top-dir rename failed; spec left untouched."; exit 1; }
fi
SRC="$TMPD/concat-$HEAD_SHA"
[ -d "$SRC/src" ] || { echo "Unexpected source layout (no src/); spec left untouched."; exit 1; }

(
    cd "$SRC/src" || exit 1
    if ! cargo vendor > ../cargo_config.tmp 2> /tmp/cargo-vendor.err; then
        cat /tmp/cargo-vendor.err
        echo "cargo vendor failed; spec left untouched."
        exit 1
    fi
    if ! head -1 ../cargo_config.tmp | grep -q "^\[source"; then
        sed -n '/^\[source/,$p' ../cargo_config.tmp > ../cargo_config
    else
        mv ../cargo_config.tmp ../cargo_config
    fi
    rm -f ../cargo_config.tmp
    mkdir -p .cargo
    cp ../cargo_config .cargo/config
) || exit 1
[ -s "$SRC/cargo_config" ] || { echo "cargo_config missing; spec left untouched."; exit 1; }

curl -fsSL --retry 3 --connect-timeout 60 "$FFMPEG_RELEASE/$FFMPEG_FILE" -o "$TMPD/ffmpeg.tar.xz" \
    || { echo "FFmpeg sidecar download failed; spec left untouched."; exit 1; }
mkdir -p "$SRC/ffmpeg-dev"
tar -xf "$TMPD/ffmpeg.tar.xz" -C "$TMPD" \
    || { echo "FFmpeg sidecar corrupt; spec left untouched."; exit 1; }
FFTOP=$(ls -d "$TMPD"/ffmpeg-n* 2>/dev/null | head -n1)
if [ -z "$FFTOP" ] || [ -z "$(ls "$FFTOP"/lib/libavcodec.* 2>/dev/null)" ] || [ ! -d "$FFTOP/include/libavcodec" ]; then
    echo "FFmpeg sidecar layout unexpected; spec left untouched."
    exit 1
fi
cp -a "$FFTOP"/lib "$FFTOP"/include "$SRC/ffmpeg-dev/"

curl -fsSL --retry 3 --connect-timeout 60 "https://github.com/microsoft/onnxruntime/releases/download/v$ORT_VERSION/$ORT_TGZ" -o "$TMPD/onnx.tgz" \
    || { echo "ONNX sidecar download failed; spec left untouched."; exit 1; }
mkdir -p "$SRC/onnxlib"
tar -xzf "$TMPD/onnx.tgz" -C "$TMPD" \
    || { echo "ONNX sidecar corrupt; spec left untouched."; exit 1; }
ONNXLIB=$(ls -d "$TMPD"/onnxruntime-linux-*/lib 2>/dev/null | head -n1)
[ -n "$ONNXLIB" ] && [ -f "$ONNXLIB/libonnxruntime.so.$ORT_VERSION" ] || { echo "ONNX sidecar layout unexpected; spec left untouched."; exit 1; }
cp -a "$ONNXLIB"/libonnxruntime.so* "$SRC/onnxlib/"
ln -sf "libonnxruntime.so.$ORT_VERSION" "$SRC/onnxlib/libonnxruntime.so"

SKIA_TAG="0.153.3"
SKIA_KEY="b7f043e0b1e2a850e702-x86_64-unknown-linux-gnu-ganesh-gl-jpegd-jpege-pdf-vulkan"
curl -fsSL --retry 3 --connect-timeout 60 \
    "https://github.com/rust-skia/skia-binaries/releases/download/$SKIA_TAG/skia-binaries-$SKIA_KEY.tar.gz" \
    -o "$TMPD/skia-binaries.tar.gz" \
    || { echo "Skia binaries download failed; spec left untouched."; exit 1; }
mkdir -p "$SRC/skia-cache"
cp -a "$TMPD/skia-binaries.tar.gz" "$SRC/skia-cache/skia-binaries-$SKIA_KEY.tar.gz"
sed -i -E "s|skia-binaries-[^\"']*\.tar\.gz|skia-binaries-$SKIA_KEY.tar.gz|g" "$SPEC_FILE" debian.rules

SHERPA_VER=$(grep -A2 'name = "sherpa-onnx-sys"' "$SRC/src/Cargo.lock" | grep '^version' | head -1 | cut -d'"' -f2)
[ -n "$SHERPA_VER" ] || { echo "sherpa-onnx-sys version unreadable; spec left untouched."; exit 1; }
SHERPA_ARCHIVE="sherpa-onnx-v$SHERPA_VER-linux-x64-static-lib.tar.bz2"
curl -fsSL --retry 3 --connect-timeout 60 \
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/v$SHERPA_VER/$SHERPA_ARCHIVE" \
    -o "$TMPD/sherpa.tar.bz2" \
    || { echo "sherpa-onnx download failed; spec left untouched."; exit 1; }
mkdir -p "$SRC/sherpa-cache"
cp -a "$TMPD/sherpa.tar.bz2" "$SRC/sherpa-cache/$SHERPA_ARCHIVE"
sed -i -E "s|sherpa-onnx-v[0-9.]+-linux-x64-static-lib\.tar\.bz2|$SHERPA_ARCHIVE|g" "$SPEC_FILE" debian.rules

rm -f concat-unstable-*.tar.gz
tar -czf "$TARBALL" -C "$TMPD" "concat-$HEAD_SHA"
ls -l "$TARBALL"
trap - EXIT
rm -rf "$TMPD"

if [ "$HEAD_SHA" != "$CURRENT_PIN" ]; then
sed -i -E "s/^%global commit.*/%global commit          $HEAD_SHA/" "$SPEC_FILE"
sed -i -E "s/^%global shortcommit.*/%global shortcommit     $SHORT/" "$SPEC_FILE"
sed -i -E "s/^%global gitdate.*/%global gitdate         $GITDATE/" "$SPEC_FILE"
sed -i -E "s/^%global base_version.*/%global base_version    $BASE_VER/" "$SPEC_FILE"
sed -i -E "s/^Version:.*/Version:        %{base_version}+git%{gitdate}.%{shortcommit}/" "$SPEC_FILE"
sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"

DSC_FILE="concat-unstable.dsc"
DSC_VER="${BASE_VER}+git${GITDATE}.${SHORT}"
sed -i -E "s/^Version: .*/Version: $DSC_VER/" "$DSC_FILE"
sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: concat-unstable-$DSC_VER.tar.gz|" "$DSC_FILE"
DEB_DATE=$(date -R -u)
DEB_ENTRY="concat-unstable ($DSC_VER-1) unstable; urgency=medium\n\n  * New upstream snapshot $SHORT (base $BASE_VER).\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
if [ -f "debian.changelog" ]; then
    echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
else
    echo -e "$DEB_ENTRY" > debian.changelog
fi

CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $DSC_VER-0\n- Update concat-unstable to base $BASE_VER + main $SHORT\n\n"

if [ -f "$CHANGES_FILE" ]; then
    echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
else
    echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
fi

echo "Success! concat-unstable at base $BASE_VER + $SHORT. Ready for OBS sync."
fi
