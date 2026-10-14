%global debug_package %{nil}
# Prevent RPM from trying to auto-generate dependencies from the bundled Electron libraries
%global __requires_exclude_from ^/opt/Heroic/.*$
%global __provides_exclude_from ^/opt/Heroic/.*$
Name:           heroic-games-launcher
Version:        2.22.3
Release:        0
Summary:        Open source GOG, Epic and Amazon games launcher
License:        GPL-3.0-only
URL:            https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher
# Use the upstream RPM as our raw source payload
Source0:        %{url}/releases/download/v2.22.3/Heroic-2.22.3-linux-x86_64.rpm
Source1:        heroic-games-launcher-rpmlintrc
# Required to unpack the upstream RPM natively
BuildRequires:  cpio
BuildRequires:  desktop-file-utils
# Explicit dependencies mapped from the payload's ELF DT_NEEDED union
# plus the upstream DEB's own Depends (libnotify/libsecret/libXss/libXtst
# tray set, xdg-utils); same proven set as the sibling Electron repacks
Requires:       at-spi2-core
Requires:       hicolor-icon-theme
Requires:       libX11.so.6()(64bit)
Requires:       libXcomposite.so.1()(64bit)
Requires:       libXdamage.so.1()(64bit)
Requires:       libXext.so.6()(64bit)
Requires:       libXfixes.so.3()(64bit)
Requires:       libXrandr.so.2()(64bit)
Requires:       libXss.so.1()(64bit)
Requires:       libXtst.so.6()(64bit)
Requires:       libasound.so.2()(64bit)
Requires:       libatk-1.0.so.0()(64bit)
Requires:       libatk-bridge-2.0.so.0()(64bit)
Requires:       libatspi.so.0()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libcups.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libexpat.so.1()(64bit)
Requires:       libgbm.so.1()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgtk-3.so.0()(64bit)
Requires:       libnotify.so.4()(64bit)
Requires:       libnspr4.so()(64bit)
Requires:       libnss3.so()(64bit)
Requires:       libnssutil3.so()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
Requires:       libsecret-1.so.0()(64bit)
Requires:       libsmime3.so()(64bit)
Requires:       libudev.so.1()(64bit)
Requires:       libuuid.so.1()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       xdg-utils
ExclusiveArch:  x86_64

%description
Heroic is a free, open-source game launcher for GOG, Epic and Amazon
Games. This version natively extracts the upstream RPM payload.

%prep
%setup -q -c -T
# Rip open the upstream RPM natively
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required for pre-built binaries

%install

# 1. Install the main application folder and standard desktop entries
install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/* %{buildroot}%{_datadir}/

# 2. Install the Electron app payload
install -d -m 0755 %{buildroot}/opt
cp -a opt/Heroic %{buildroot}/opt/

# Upstream ships chrome-sandbox 0755 (userns path, same policy as
# stoat-desktop); normalize in case a future build flips it setuid.
chmod 0755 %{buildroot}/opt/Heroic/chrome-sandbox

# 3. Create the Wayland-aware launcher wrapper
install -d -m 0755 %{buildroot}%{_bindir}
cat <<-'EOF' > %{buildroot}%{_bindir}/heroic
#!/bin/sh
# Automatically force native Wayland rendering if detected
if [ "$XDG_SESSION_TYPE" = "wayland" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    export ELECTRON_OZONE_PLATFORM_HINT="auto"
fi
exec /opt/Heroic/heroic "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/heroic

# 4. Point the desktop entry at the wrapper
sed -i -e 's|^Exec=.*|Exec=/usr/bin/heroic %U|' \
    %{buildroot}%{_datadir}/applications/heroic.desktop

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/heroic.desktop

%files
%license /opt/Heroic/LICENSE.electron.txt
%doc /opt/Heroic/LICENSES.chromium.html
%exclude /opt/Heroic/LICENSE.electron.txt
%exclude /opt/Heroic/LICENSES.chromium.html
%{_bindir}/heroic
%{_datadir}/applications/heroic.desktop
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/*
%dir %{_datadir}/icons/hicolor/*/apps
%{_datadir}/icons/hicolor/*/apps/heroic.png
/opt/Heroic/

%changelog
