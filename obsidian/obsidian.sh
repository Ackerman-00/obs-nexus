#!/bin/bash
OBSIDIAN_USER_FLAGS_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/obsidian/user-flags.conf"

if [ -f "$OBSIDIAN_USER_FLAGS_FILE" ]; then
   mapfile -t OBSIDIAN_USER_FLAGS < <(sed -r "/^( *#|$)/d;s% %\n%g" "$OBSIDIAN_USER_FLAGS_FILE")
fi

if [ "$XDG_SESSION_TYPE" = "wayland" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    export ELECTRON_OZONE_PLATFORM_HINT="${ELECTRON_OZONE_PLATFORM_HINT:-auto}"
fi

exec /opt/obsidian/obsidian "${OBSIDIAN_USER_FLAGS[@]}" "$@"
