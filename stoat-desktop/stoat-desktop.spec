%global debug_package %{nil}
%global __requires_exclude_from ^/opt/Stoat/.*$
%global __provides_exclude_from ^/opt/Stoat/.*$
Name:           stoat-desktop
Version:        1.5.4
Release:        0
Summary:        Open source, user-first chat platform desktop client
License:        AGPL-3.0-only AND MIT AND BSD-2-Clause
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
Requires:       libgcc_s.so.1()(64bit)
Requires:       libpipewire-0_3-0
Requires:       libpulse.so.0()(64bit)
Requires:       libsecret-1-0
Requires:       libsystemd0
Requires:       libxcb1
Requires:       libxkbcommon0
Requires:       mozilla-nss
Requires:       xdg-utils
Requires(post): desktop-file-utils
Requires(posttrans): gtk3-tools
Requires(postun): gtk3-tools
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

%install

install -d -m 0755 %{buildroot}/opt/Stoat
cp -a Stoat-linux-x64/* %{buildroot}/opt/Stoat/

install -Dpm 0644 %{SOURCE1} %{buildroot}%{_datadir}/applications/chat.stoat.StoatDesktop.desktop
install -Dpm 0644 %{SOURCE2} %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/chat.stoat.StoatDesktop.png
install -Dpm 0644 %{SOURCE3} %{buildroot}%{_datadir}/metainfo/chat.stoat.StoatDesktop.metainfo.xml

install -d -m 0755 %{buildroot}%{_bindir}
cat <<-'EOF' > %{buildroot}%{_bindir}/stoat-desktop
#!/bin/sh
if [ "$XDG_SESSION_TYPE" = "wayland" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    export ELECTRON_OZONE_PLATFORM_HINT="auto"
fi
exec /opt/Stoat/stoat-desktop "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/stoat-desktop

chmod 0755 %{buildroot}/opt/Stoat/chrome-sandbox

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/chat.stoat.StoatDesktop.desktop

%post
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

%files
%{_bindir}/stoat-desktop
%{_datadir}/applications/chat.stoat.StoatDesktop.desktop
%{_datadir}/icons/hicolor/256x256/apps/chat.stoat.StoatDesktop.png
%{_datadir}/metainfo/chat.stoat.StoatDesktop.metainfo.xml
/opt/Stoat/

%changelog
