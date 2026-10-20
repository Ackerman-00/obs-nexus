%global debug_package %{nil}
# Prevent RPM from trying to auto-generate dependencies from the bundled Electron libraries
%global __requires_exclude_from ^/opt/Vesktop/.*$
%global __provides_exclude_from ^/opt/Vesktop/.*$
Name:           vesktop
Version:        1.6.7
Release:        0
Summary:        Custom Discord desktop client with Vencord preinstalled
License:        GPL-3.0-or-later
Group:          Productivity/Networking/Talk/Clients
URL:            https://github.com/Vencord/Vesktop
Source0:        https://github.com/Vencord/Vesktop/releases/download/v1.6.7/vesktop-1.6.7.x86_64.rpm
# Source1 is the filter file to bypass the "Badness" check
Source1:        vesktop-rpmlintrc
BuildRequires:  cpio
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
# Runtime dependencies for the bundled Electron/Chromium runtime
Requires:       at-spi2-core
Requires:       libX11.so.6()(64bit)
Requires:       libXcomposite.so.1()(64bit)
Requires:       libXdamage.so.1()(64bit)
Requires:       libXext.so.6()(64bit)
Requires:       libXfixes.so.3()(64bit)
Requires:       libXrandr.so.2()(64bit)
Requires:       libasound.so.2()(64bit)
Requires:       libatk-1.0.so.0()(64bit)
Requires:       libatk-bridge-2.0.so.0()(64bit)
Requires:       libatspi.so.0()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libcups.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libexpat.so.1()(64bit)
Requires:       libgbm.so.1()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgtk-3.so.0()(64bit)
Requires:       libnotify.so.4()(64bit)
Requires:       libnspr4.so()(64bit)
Requires:       libnss3.so()(64bit)
Requires:       libnssutil3.so()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
# dlopen-only at runtime (not DT_NEEDED, so invisible to auto-deps):
# libsecret for the OS keyring (Chromium os_crypt), libpulse for audio
# playback, libpipewire for screen-share audio capture - all proven by
# strings in the shipped 1.6.7 main binary (same Electron code path as
# fluxer, whose spec declares them).
Requires:       libpipewire-0.3.so.0()(64bit)
Requires:       libpulse.so.0()(64bit)
Requires:       libsecret-1.so.0()(64bit)
Requires:       libsmime3.so()(64bit)
Requires:       libudev.so.1()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       xdg-utils
Provides:       vencorddesktop = %{version}-%{release}
Provides:       vesktop = %{version}-%{release}
Obsoletes:      vencorddesktop < %{version}
ExclusiveArch:  x86_64

%description
Vesktop is a custom Discord client designed to enhance your experience.
Repackaged for openSUSE with auto-Wayland support.

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required

%install

# 1. Install main app
install -d -m 0755 %{buildroot}/opt/Vesktop
cp -a opt/Vesktop/* %{buildroot}/opt/Vesktop/

# 2. Install icons and desktop files
install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/

# 3. Native Wayland Wrapper
install -d -m 0755 %{buildroot}%{_bindir}
cat <<-'EOF' > %{buildroot}%{_bindir}/vesktop
#!/bin/sh
if [ "$XDG_SESSION_TYPE" = "wayland" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    export ELECTRON_OZONE_PLATFORM_HINT="auto"
fi
exec /opt/Vesktop/vesktop "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/vesktop

%check
# Upstream desktop file is already correct; validate it instead of the
# deprecated suse_update_desktop_file macro (rpmlint:
# suse-update-desktop-file-deprecated).
desktop-file-validate %{buildroot}%{_datadir}/applications/vesktop.desktop

%files
%{_bindir}/vesktop
%{_datadir}/applications/vesktop.desktop
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/*
%dir %{_datadir}/icons/hicolor/*/apps
%{_datadir}/icons/hicolor/*/apps/*.*
%dir /opt/Vesktop
%exclude /opt/Vesktop/chrome-sandbox
/opt/Vesktop/*
%attr(4755, root, root) /opt/Vesktop/chrome-sandbox

%changelog
