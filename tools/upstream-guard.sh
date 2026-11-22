#!/bin/bash
# #asset-guard: release assets 404 briefly after publication (CDN propagation).

# #nvr-bullet: the .changes entry must name the Release the spec will build
spec_release() {
    local spec="${1:-}" rel=""
    [ -n "$spec" ] && [ -f "$spec" ] || spec=$(ls ./*.spec 2>/dev/null | head -1)
    [ -n "$spec" ] && rel=$(sed -n 's/^Release:[[:space:]]*//p' "$spec" | head -1)
    printf '%s\n' "${rel:-0}"
}

asset_http_ok() {
    local url="$1" attempts="${2:-4}" delay="${3:-5}" code=""
    local i=1
    while [ "$i" -le "$attempts" ]; do
        code=$(command curl -s -o /dev/null -w '%{http_code}' -L --max-time 60 "$url" 2>/dev/null)
        case "$code" in
            200|206) return 0 ;;
        esac
        [ "$i" -lt "$attempts" ] && sleep "$delay" && delay=$(( delay * 2 ))
        i=$(( i + 1 ))
    done
    ASSET_HTTP_CODE="$code"
    return 1
}
