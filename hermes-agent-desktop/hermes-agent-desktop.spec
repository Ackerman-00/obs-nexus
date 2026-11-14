%global debug_package %{nil}
%global __requires_exclude_from ^/opt/HermesDesktop/.*$
%global __provides_exclude_from ^/opt/HermesDesktop/.*$
%global __brp_mangle_shebangs_exclude_from ^/opt/HermesDesktop/.*$
%global commit          422ad1861856dd9b80b947fbad9f39d1580f6b41
%global shortcommit     422ad18
%global gitdate         20261114034817
%global base_version    0.23.1

Name:           hermes-agent-desktop
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        Native desktop shell for Hermes Agent (git snapshot)
License:        MIT
Group:          Development/Tools/IDE
URL:            https://github.com/NousResearch/hermes-agent
Source0:        hermes-agent-desktop-%{version}.tar.gz
Source1:        hermes-agent-desktop-rpmlintrc
ExclusiveArch:  x86_64

BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
Requires:       at-spi2-core
Requires:       hicolor-icon-theme
Requires:       mozilla-nss
Requires:       xdg-utils
Requires:       libasound.so.2()(64bit)
Requires:       libatk-1.0.so.0()(64bit)
Requires:       libatk-bridge-2.0.so.0()(64bit)
Requires:       libatspi.so.0()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libcups.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libdrm.so.2()(64bit)
Requires:       libexpat.so.1()(64bit)
Requires:       libgbm.so.1()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgtk-3.so.0()(64bit)
Requires:       libnspr4.so()(64bit)
Requires:       libnss3.so()(64bit)
Requires:       libnssutil3.so()(64bit)
Requires:       libnotify.so.4()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
Requires:       libpipewire-0.3.so.0()(64bit)
Requires:       libpulse.so.0()(64bit)
Requires:       libsecret-1.so.0()(64bit)
Requires:       libsmime3.so()(64bit)
Requires:       libstdc++.so.6()(64bit)
Requires:       libudev.so.1()(64bit)
Requires:       libXi.so.6()(64bit)
Requires:       libX11.so.6()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libXcomposite.so.1()(64bit)
Requires:       libXdamage.so.1()(64bit)
Requires:       libXext.so.6()(64bit)
Requires:       libXfixes.so.3()(64bit)
Requires:       libXrandr.so.2()(64bit)
Requires:       libXss.so.1()(64bit)
Requires:       libXtst.so.6()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       libuuid.so.1()(64bit)
Requires(posttrans): gtk3-tools
Requires(postun): gtk3-tools
Recommends:     ffmpeg

%description
Hermes Agent desktop: chat sessions, background agent work, file browsing and
management, integrated terminal and browser, previews, sessions, memory and
skills. This package is repackaged from the upstream git snapshot built by the
repo's own CI pipeline (the OBS build container has no network, so the build
itself happens in CI; OBS repacks the result offline).

%prep
%setup -q -n hermes-agent-desktop-%{version}

%build

%install
install -d %{buildroot}/opt/HermesDesktop %{buildroot}%{_bindir}
if [ -d linux-unpacked ]; then
    cp -a linux-unpacked/* %{buildroot}/opt/HermesDesktop/
else
    echo "ERROR: CI-built payload missing linux-unpacked/" >&2
    exit 1
fi
ICON=$(find . -name 'hermes.png' | head -n1)
[ -n "$ICON" ] || { echo "ERROR: no hermes.png in payload" >&2; exit 1; }
install -Dpm0644 "$ICON" %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/hermes-agent-desktop.png

cat > %{buildroot}%{_bindir}/hermes-agent-desktop <<'WRAPPER_EOF'
#!/bin/sh
exec /opt/HermesDesktop/Hermes "$@"
WRAPPER_EOF
chmod 755 %{buildroot}%{_bindir}/hermes-agent-desktop

install -d %{buildroot}%{_datadir}/applications
cat > %{buildroot}%{_datadir}/applications/hermes-agent-desktop.desktop <<'DESKTOP_EOF'
[Desktop Entry]
Type=Application
Name=Hermes Agent Desktop
Comment=Native desktop shell for Hermes Agent
Exec=hermes-agent-desktop %U
Terminal=false
Categories=Development;
Icon=hermes-agent-desktop
DESKTOP_EOF

%post
/bin/touch --no-create %{_datadir}/icons/hicolor >/dev/null 2>&1 || :
/usr/bin/gtk-update-icon-cache -q %{_datadir}/icons/hicolor >/dev/null 2>&1 || :
if ! { [ -L /proc/self/ns/user ] && unshare --user true; }; then
    chmod 4755 /opt/HermesDesktop/chrome-sandbox || :
else
    chmod 0755 /opt/HermesDesktop/chrome-sandbox || :
fi

%postun
case "$1" in
    0)
        /bin/touch --no-create %{_datadir}/icons/hicolor >/dev/null 2>&1
        /usr/bin/gtk-update-icon-cache -q %{_datadir}/icons/hicolor >/dev/null 2>&1 || :
        ;;
esac

%posttrans
/usr/bin/gtk-update-icon-cache -q %{_datadir}/icons/hicolor >/dev/null 2>&1 || :

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/hermes-agent-desktop.desktop

%files
/opt/HermesDesktop/
%license LICENSE
%{_bindir}/hermes-agent-desktop
%{_datadir}/applications/hermes-agent-desktop.desktop
%{_datadir}/icons/hicolor/512x512/apps/hermes-agent-desktop.png

%changelog
