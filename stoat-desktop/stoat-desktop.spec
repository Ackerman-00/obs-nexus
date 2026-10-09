# Disable debuginfo extraction since we are repackaging pre-compiled binaries
%global debug_package %{nil}
# Prevent RPM from trying to auto-generate dependencies from the bundled Electron libraries
%global __requires_exclude_from ^/opt/Stoat/.*$
%global __provides_exclude_from ^/opt/Stoat/.*$
Name:           stoat-desktop
Version:        1.5.4
Release:        0
Summary:        Open source, user-first chat platform desktop client
License:        AGPL-3.0-only AND MIT AND BSD-2-Clause
# FIXME: use correct group or remove it, see "https://en.opensuse.org/openSUSE:Package_group_guidelines"
Group:          Productivity/Networking/Talk/Clients
URL:            https://github.com/stoatchat/for-desktop
Source0:        %{url}/releases/download/v%{version}/Stoat-linux-x64-%{version}.zip
Source1:        stoat-desktop.desktop
Source2:        stoat.png
Source3:        chat.stoat.StoatDesktop.metainfo.xml
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
BuildRequires:  unzip
Requires:       at-spi2-core
Requires:       dbus-1
Requires:       gtk3
Requires:       libX11-6
Requires:       libXcomposite1
Requires:       libXdamage1
Requires:       libXext6
Requires:       libXfixes3
Requires:       libXrandr2
Requires:       libasound2
Requires:       libcups2
Requires:       libgbm1
Requires:       libsecret-1-0
Requires:       libsystemd0
Requires:       libxcb1
Requires:       libxkbcommon0
Requires:       mozilla-nss
Requires:       xdg-utils
Requires(post): desktop-file-utils
Requires(posttrans): gtk3-tools
Requires(postun): gtk3-tools
# chrome-sandbox ships setuid: register it with the permissions system
# (rpmlint permissions-missing-* otherwise, Badness 10).
PreReq: permissions
ExclusiveArch:  x86_64

%description
Stoat is an open source, user-first chat platform. Send messages, share
images, mention users, and join voice channels — all from a native desktop
application. Packaged from the upstream pre-built Electron bundle for the
Nexus repository.

%prep
%setup -q -c -T
unzip -q %{SOURCE0}

%build
# No compilation required for pre-built binaries

%install

# 1. Install the main application folder
install -d -m 0755 %{buildroot}/opt/Stoat
cp -a Stoat-linux-x64/* %{buildroot}/opt/Stoat/

# 2. Install desktop entry, icon and metainfo
install -Dpm 0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/chat.stoat.StoatDesktop.desktop
install -Dpm 0644 %{SOURCE2} %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/chat.stoat.StoatDesktop.png
install -Dpm 0644 %{SOURCE3} %{buildroot}%{_datadir}/metainfo/chat.stoat.StoatDesktop.metainfo.xml

# 3. Create the Wayland-aware wrapper script
install -d -m 0755 %{buildroot}%{_bindir}
cat <<-'EOF' > %{buildroot}%{_bindir}/stoat-desktop
#!/bin/sh
# Automatically force native Wayland rendering if detected
if [ "$XDG_SESSION_TYPE" = "wayland" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    export ELECTRON_OZONE_PLATFORM_HINT="auto"
fi
exec /opt/Stoat/stoat-desktop "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/stoat-desktop

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/chat.stoat.StoatDesktop.desktop

%post
%set_permissions /opt/Stoat/chrome-sandbox
# Refresh the desktop database and icon cache
%{_bindir}/update-desktop-database > /dev/null 2>&1 || :
/bin/touch --no-create %{_datadir}/icons/hicolor > /dev/null 2>&1 || :

%postun
%{_bindir}/update-desktop-database > /dev/null 2>&1 || :
case "$1" in
    0)
        /bin/touch --no-create %{_datadir}/icons/hicolor > /dev/null 2>&1
        %{_bindir}/gtk-update-icon-cache %{_datadir}/icons/hicolor > /dev/null 2>&1 || :
        ;;
esac

%posttrans
%{_bindir}/gtk-update-icon-cache %{_datadir}/icons/hicolor > /dev/null 2>&1 || :

%verifyscript
%verify_permissions -e /opt/Stoat/chrome-sandbox

%files
%{_bindir}/stoat-desktop
%{_datadir}/applications/chat.stoat.StoatDesktop.desktop
%{_datadir}/icons/hicolor/256x256/apps/chat.stoat.StoatDesktop.png
%{_datadir}/metainfo/chat.stoat.StoatDesktop.metainfo.xml
/opt/Stoat/
# Enforce strict sandbox permissions natively
%attr(4755, root, root) /opt/Stoat/chrome-sandbox

%changelog
