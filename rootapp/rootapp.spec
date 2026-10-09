%global debug_package %{nil}
%global __os_install_post %{nil}
%global __requires_exclude_from ^/opt/rootapp/.*$
%global __provides_exclude_from ^/opt/rootapp/.*$
Name:           rootapp
Version:        0.9.147
Release:        0
Summary:        Discord alternative for gaming communities and large groups
License:        Proprietary
URL:            https://www.rootapp.com
Source0:        https://installer.rootapp.com/installer/Linux/X64/Root.AppImage
BuildRequires:  binutils
BuildRequires:  hicolor-icon-theme
BuildRequires:  python3
BuildRequires:  squashfs
Requires:       Mesa-libEGL1
Requires:       alsa
Requires:       at-spi2-core
Requires:       hicolor-icon-theme
Requires:       libX11.so.6()(64bit)
Requires:       libXcomposite.so.1()(64bit)
Requires:       libXcursor.so.1()(64bit)
Requires:       libXdamage.so.1()(64bit)
Requires:       libXrandr.so.2()(64bit)
Requires:       libXrender.so.1()(64bit)
Requires:       libXss.so.1()(64bit)
Requires:       libXt.so.6()(64bit)
Requires:       libXtst.so.6()(64bit)
Requires:       libgbm.so.1()(64bit)
Requires:       libgtk-3.so.0()(64bit)
Requires:       libnotify.so.4()(64bit)
Requires:       libpulse.so.0()(64bit)
Requires:       libvulkan.so.1()(64bit)
Requires:       libwayland-client.so.0()(64bit)
Requires:       libwayland-cursor.so.0()(64bit)
Requires:       libwayland-egl.so.1()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       mozilla-nspr
Requires:       mozilla-nss
Requires:       wl-clipboard
Requires:       xdg-utils
Provides:       rootapp = %{version}-%{release}
# sha256: e92cb96e0ca5227b73946a7e181c11ce3f4ba7f2e72b864a84ba03841065ddd6
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

# Set SUID on chrome-sandbox if present (Electron sandbox)
if [ -f "%{buildroot}/opt/rootapp/chrome-sandbox" ]; then
    chmod 4755 %{buildroot}/opt/rootapp/chrome-sandbox
fi

install -dm755 %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/rootapp <<'WRAPPER_EOF'
#!/bin/sh
export APPDIR="/opt/rootapp"
exec /opt/rootapp/AppRun "$@"
WRAPPER_EOF
chmod 755 %{buildroot}%{_bindir}/rootapp

install -Dm644 squashfs-root/Root.png %{buildroot}%{_datadir}/pixmaps/rootapp.png
install -Dm644 squashfs-root/Root.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/rootapp.png

install -dm755 %{buildroot}%{_datadir}/applications/
cat > %{buildroot}%{_datadir}/applications/rootapp.desktop <<DESKTOP_EOF
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
%{_datadir}/applications/rootapp.desktop
%{_datadir}/icons/hicolor/*/apps/rootapp.png
%{_datadir}/pixmaps/rootapp.png

%changelog
