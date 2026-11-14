#!/bin/bash
# owner 2026-11-14: auto-update disabled; updates are published by Ackerman-00
if [ -z "${NEXUS_OWNER_UPDATE:-}" ]; then
    echo "auto-update disabled (owner rule 2026-11-14); updates are published manually by Ackerman-00"
    exit 0
fi
cd "$(dirname "$0")" || exit 1

SPEC_FILE="hermes-agent-desktop.spec"
CHANGES_FILE="hermes-agent-desktop.changes"
GITHUB_REPO="NousResearch/hermes-agent"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

BK=$(mktemp -d)
BK_FILES="$SPEC_FILE $CHANGES_FILE hermes-agent-desktop.dsc debian.changelog"
for f in $BK_FILES; do [ -f "$f" ] && cp -p "$f" "$BK/"; done
trap 'rc=$?; if [ "$rc" != "0" ]; then for f in $BK_FILES; do if [ -f "$f" ] && [ -f "$BK/$(basename "$f")" ]; then cp -p "$BK/$(basename "$f")" "$f"; fi; done; fi; rm -rf "$BK"' EXIT

echo "Checking for upstream updates on $GITHUB_REPO..."

LATEST_COMMIT=$(git ls-remote "https://github.com/$GITHUB_REPO.git" HEAD 2>/dev/null | awk '{print $1}')
if [ -z "$LATEST_COMMIT" ]; then
    echo "Error: Failed to fetch HEAD commit."
    exit 1
fi

LATEST_TAG=$(git ls-remote --tags "https://github.com/$GITHUB_REPO.git" 2>/dev/null | awk '{print $2}' | sed 's|refs/tags/||;s/\^{}//' | grep -E '^v0\.[0-9]+\.[0-9]+$' | sort -V | tail -1)
if [ -z "$LATEST_TAG" ]; then
    echo "Error: no stable v0.x.y tag found upstream."
    exit 1
fi

BASE_VER="${LATEST_TAG#v}"
SHORT=${LATEST_COMMIT:0:7}
CURRENT_COMMIT=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')
CURRENT_BASE=$(grep -E "^%global base_version" "$SPEC_FILE" | awk '{print $3}')
CURRENT_GITDATE=$(grep -E "^%global gitdate" "$SPEC_FILE" | awk '{print $3}')
CURRENT_SHORT=$(grep -E "^%global shortcommit" "$SPEC_FILE" | awk '{print $3}')
CURRENT_VER="$CURRENT_BASE+git$CURRENT_GITDATE.$CURRENT_SHORT"

need_bump=0
if [ "$CURRENT_COMMIT" != "$LATEST_COMMIT" ] || [ "$CURRENT_BASE" != "$BASE_VER" ]; then
    need_bump=1
fi

if [ "$need_bump" = "1" ]; then
    COMMIT_DATE_RAW=$(curl -sL -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/commits/$LATEST_COMMIT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('commit',{}).get('committer',{}).get('date',''))" 2>/dev/null)
    if [ -z "$COMMIT_DATE_RAW" ]; then
        echo "Error: Failed to fetch the commit date."
        exit 1
    fi
    GIT_DATE=$(echo "$COMMIT_DATE_RAW" | sed 's/[-T:Z]//g')
    NEW_VER="$BASE_VER+git$GIT_DATE.$SHORT"

    sed -i -E "s/^%global commit.*/%global commit          $LATEST_COMMIT/" "$SPEC_FILE"
    sed -i -E "s/^%global shortcommit.*/%global shortcommit     $SHORT/" "$SPEC_FILE"
    sed -i -E "s/^%global gitdate.*/%global gitdate         $GIT_DATE/" "$SPEC_FILE"
    sed -i -E "s/^%global base_version.*/%global base_version    $BASE_VER/" "$SPEC_FILE"
    sed -i -E "s/^Version:.*/Version:        %{base_version}+git%{gitdate}.%{shortcommit}/" "$SPEC_FILE"
    sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"
else
    NEW_VER="$CURRENT_VER"
fi

OUT="hermes-agent-desktop-$NEW_VER.tar.gz"
if [ ! -f "$OUT" ]; then
    if [ -n "$OBS_USER" ] && [ -n "$OBS_PASS" ] && curl -fsSL -u "$OBS_USER:$OBS_PASS" -o "$OUT" "https://api.opensuse.org/source/home:ackerman/hermes-agent-desktop/$OUT"; then
        echo "payload restored from OBS (no rebuild needed)"
    else
        rm -f "$OUT"
        if ! bash build.sh; then
            echo "CI-only payload build unavailable or failed."
            if [ "$need_bump" = "0" ]; then
                echo "No version change and no payload; leaving the tree untouched."
                exit 0
            fi
            echo "ERROR: refusing to bump the version without a built payload."
            exit 1
        fi
    fi
fi

if [ "$need_bump" = "1" ]; then

    DSC_FILE="hermes-agent-desktop.dsc"
    sed -i -E "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
    sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: hermes-agent-desktop-$NEW_VER.tar.gz|" "$DSC_FILE"

    DEB_DATE=$(date -R -u)
    DEB_ENTRY="hermes-agent-desktop ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream snapshot $SHORT (base $BASE_VER).\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
    if [ -f "debian.changelog" ]; then
        echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
    else
        echo -e "$DEB_ENTRY" > debian.changelog
    fi

    CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
    NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $NEW_VER-0\n- Update hermes-agent-desktop to base $BASE_VER + main $SHORT\n\n"

    if [ -f "$CHANGES_FILE" ]; then
        echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
    else
        echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
    fi

    echo "Updated to $NEW_VER."
else
    echo "Package is already at main $SHORT (base $BASE_VER). No update needed."
fi
