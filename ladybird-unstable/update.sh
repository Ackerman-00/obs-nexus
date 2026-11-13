#!/bin/bash
cd "$(dirname "$0")" || exit 1

SPEC_FILE="ladybird-unstable.spec"
CHANGES_FILE="ladybird-unstable.changes"
GITHUB_REPO="LadybirdBrowser/ladybird"
PACKAGER="Ackerman-00"
PACKAGER_ADDR="Ackerman-00 <noreply@example.com>"

echo "Checking for upstream updates on $GITHUB_REPO..."

LATEST_COMMIT=$(git ls-remote "https://github.com/$GITHUB_REPO.git" HEAD 2>/dev/null | awk '{print $1}')
if [ -z "$LATEST_COMMIT" ]; then
    echo "Error: Failed to fetch HEAD commit."
    exit 1
fi

SHORT=${LATEST_COMMIT:0:7}
CURRENT_COMMIT=$(grep -E "^%global commit" "$SPEC_FILE" | awk '{print $3}')
CURRENT_GITDATE=$(grep -E "^%global gitdate" "$SPEC_FILE" | awk '{print $3}')
CURRENT_SHORT=$(grep -E "^%global shortcommit" "$SPEC_FILE" | awk '{print $3}')
CURRENT_BASE=$(grep -E "^%global base_version" "$SPEC_FILE" | awk '{print $3}')
CURRENT_VER="$CURRENT_BASE+git$CURRENT_GITDATE.$CURRENT_SHORT"

need_bump=0
if [ "$CURRENT_COMMIT" != "$LATEST_COMMIT" ]; then
    need_bump=1
fi

if [ "$need_bump" = "1" ]; then
    COMMIT_DATE_RAW=$(curl -sL -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$GITHUB_REPO/commits/$LATEST_COMMIT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('commit',{}).get('committer',{}).get('date',''))" 2>/dev/null)
    if [ -z "$COMMIT_DATE_RAW" ]; then
        echo "Error: Failed to fetch the commit date."
        exit 1
    fi
    GIT_DATE=$(echo "$COMMIT_DATE_RAW" | sed 's/[-T:Z]//g')
    BASE_VER=$(grep -E "^%global base_version" "$SPEC_FILE" | awk '{print $3}')
    NEW_VER="$BASE_VER+git$GIT_DATE.$SHORT"

    sed -i -E "s/^%global commit.*/%global commit         $LATEST_COMMIT/" "$SPEC_FILE"
    sed -i -E "s/^%global shortcommit.*/%global shortcommit     $SHORT/" "$SPEC_FILE"
    sed -i -E "s/^%global gitdate.*/%global gitdate         $GIT_DATE/" "$SPEC_FILE"
    sed -i -E "s/^Version:.*/Version:        %{base_version}+git%{gitdate}.%{shortcommit}/" "$SPEC_FILE"
    sed -i -E "s/^Release:.*/Release:        0/" "$SPEC_FILE"
    OUT="ladybird-unstable-$NEW_VER.tar.gz"
    rm -f "$OUT"
else
    NEW_VER="$CURRENT_VER"
    OUT="ladybird-unstable-$NEW_VER.tar.gz"
fi

if [ ! -f "$OUT" ]; then
    if [ -n "$OBS_USER" ] && [ -n "$OBS_PASS" ] && curl -fsSL -u "$OBS_USER:$OBS_PASS" -o "$OUT" "https://api.opensuse.org/source/home:ackerman/ladybird-unstable/$OUT"; then
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
    CURRENT_DATE=$(LC_ALL=C date -u +"%a %b %d %T UTC %Y")
    NEW_CHANGELOG_ENTRY="-------------------------------------------------------------------\n$CURRENT_DATE - $PACKAGER_ADDR\n\n- version $NEW_VER-0\n- Update ladybird-unstable to main $SHORT\n\n"

    if [ -f "$CHANGES_FILE" ]; then
        echo -e "$NEW_CHANGELOG_ENTRY$(cat $CHANGES_FILE)" > "$CHANGES_FILE"
    else
        echo -e "$NEW_CHANGELOG_ENTRY" > "$CHANGES_FILE"
    fi

    DEB_DATE=$(date -R -u)
    DEB_ENTRY="ladybird-unstable ($NEW_VER-1) unstable; urgency=medium\n\n  * New upstream snapshot $SHORT.\n\n -- $PACKAGER <noreply@example.com>  $DEB_DATE\n\n"
    if [ -f "debian.changelog" ]; then
        echo -e "${DEB_ENTRY}$(cat debian.changelog)" > debian.changelog
    else
        echo -e "$DEB_ENTRY" > debian.changelog
    fi

    DSC_FILE="ladybird-unstable.dsc"
    sed -i -E "s/^Version: .*/Version: $NEW_VER/" "$DSC_FILE"
    sed -i -E "s|^Debtransform-Tar:.*|Debtransform-Tar: ladybird-unstable-$NEW_VER.tar.gz|" "$DSC_FILE"

    echo "Updated to $NEW_VER."
else
    echo "Package is already at main $SHORT. No update needed."
fi
