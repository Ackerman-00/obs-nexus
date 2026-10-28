%global debug_package %{nil}
%global __os_install_post %{nil}
%global __requires_exclude_from ^/opt/rootapp/.*$
%global __provides_exclude_from ^/opt/rootapp/.*$
Name:           rootapp
Version:        0.9.156
Release:        0
Summary:        Discord alternative for gaming communities and large groups
License:        SUSE-Freeware
URL:            https://www.rootapp.com
Source0:        https://installer.rootapp.com/installer/Linux/X64/Root.AppImage
BuildRequires:  binutils
BuildRequires:  hicolor-icon-theme
BuildRequires:  squashfs
Requires:       at-spi2-core
Requires:       hicolor-icon-theme
Requires:       mozilla-nspr
Requires:       mozilla-nss
Requires:       xdg-utils
# --- sonames: DT_NEEDED union (see above) -------------------------------
Requires:       libX11.so.6()(64bit)
Requires:       libXcomposite.so.1()(64bit)
Requires:       libXdamage.so.1()(64bit)
Requires:       libXext.so.6()(64bit)
Requires:       libXfixes.so.3()(64bit)
Requires:       libXinerama.so.1()(64bit)
Requires:       libXrandr.so.2()(64bit)
Requires:       libXt.so.6()(64bit)
Requires:       libXtst.so.6()(64bit)
Requires:       libasound.so.2()(64bit)
Requires:       libatk-1.0.so.0()(64bit)
Requires:       libatk-bridge-2.0.so.0()(64bit)
Requires:       libatspi.so.0()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libcups.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libexpat.so.1()(64bit)
Requires:       libfontconfig.so.1()(64bit)
Requires:       libgbm.so.1()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libgdk-3.so.0()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgtk-3.so.0()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
Requires:       libstdc++.so.6()(64bit)
Requires:       libudev.so.1()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
# --- sonames: loaded by name at runtime (dlopen / .NET probe table) -----
Requires:       libEGL.so.1()(64bit)
Requires:       libGL.so.1()(64bit)
Requires:       libICE.so.6()(64bit)
Requires:       libSM.so.6()(64bit)
Requires:       libX11-xcb.so.1()(64bit)
Requires:       libXcursor.so.1()(64bit)
Requires:       libXi.so.6()(64bit)
Requires:       libXss.so.1()(64bit)
Requires:       libgssapi_krb5.so.2()(64bit)
Requires:       libpipewire-0.3.so.0()(64bit)
Requires:       libpulse.so.0()(64bit)
Requires:       libssl.so.3()(64bit)
Requires:       libva-drm.so.2()(64bit)
Requires:       libva.so.2()(64bit)
Requires:       libvulkan.so.1()(64bit)
Requires:       libwayland-client.so.0()(64bit)
Provides:       rootapp = %{version}-%{release}
# sha256: 827f991a6b4b94c3c07dc7403b7dd6fbceff353e787e4c5967772a30021cdcb0
ExclusiveArch:  x86_64

%description
Root App is a new Discord alternative, designed for gaming communities and
large online groups.

%prep
%setup -q -c -T

OFFSET=$(LC_ALL=C readelf -h %{SOURCE0} | awk 'NR==13{e_shoff=$5} NR==18{e_shentsize=$5} NR==19{e_shnum=$5} END{print e_shoff+e_shentsize*e_shnum}')
unsquashfs -q -d squashfs-root -o "$OFFSET" %{SOURCE0}
chmod go-w squashfs-root

%build

%install
install -dm755 %{buildroot}/opt/rootapp
cp -ar squashfs-root/* %{buildroot}/opt/rootapp/

rm -f %{buildroot}/opt/rootapp/usr/bin/Root.dbg


install -dm755 %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/rootapp <<'WRAPPER_EOF'
#!/bin/sh
export APPDIR="/opt/rootapp"
exec /opt/rootapp/AppRun "$@"
WRAPPER_EOF
chmod 755 %{buildroot}%{_bindir}/rootapp

install -Dm644 squashfs-root/Root.png %{buildroot}%{_datadir}/pixmaps/rootapp.png
install -Dm644 squashfs-root/Root.png %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/rootapp.png

install -dm755 %{buildroot}%{_datadir}/applications/
cat > %{buildroot}%{_datadir}/applications/rootapp-app.desktop <<DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=Root
Comment=Root App is a new Discord alternative, designed for gaming communities and large online groups
Exec=rootapp %U
Icon=rootapp
Terminal=false
StartupWMClass=Root
Categories=Network;InstantMessaging;
MimeType=x-scheme-handler/rootapp;
DESKTOP_EOF

%files
%{_bindir}/rootapp
/opt/rootapp/
%{_datadir}/applications/rootapp-app.desktop
%{_datadir}/icons/hicolor/*/apps/rootapp.png
%{_datadir}/pixmaps/rootapp.png

%changelog
