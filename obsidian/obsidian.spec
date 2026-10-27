%global app_id md.obsidian.Obsidian
%global debug_package %{nil}
%global __requires_exclude_from ^/opt/obsidian/.*$
%global __provides_exclude_from ^/opt/obsidian/.*$
Name:           obsidian
Version:        1.14.5
Release:        0
Summary:        A powerful knowledge base for plain text Markdown files
License:        NonFree
Group:          Productivity/Text/Editors
URL:            https://obsidian.md/
Source0:        Obsidian-%{version}.AppImage
Source2:        obsidian.sh
Source3:        obsidian-rpmlintrc
BuildRequires:  binutils
BuildRequires:  desktop-file-utils
BuildRequires:  fdupes
BuildRequires:  hicolor-icon-theme
BuildRequires:  squashfs
Requires:       bash
Requires:       at-spi2-core
Requires:       hicolor-icon-theme
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
Requires:       libfontconfig.so.1()(64bit)
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
Requires:       libpipewire-0.3.so.0()(64bit)
Requires:       libpulse.so.0()(64bit)
Requires:       libsecret-1.so.0()(64bit)
Requires:       libsmime3.so()(64bit)
Requires:       libstdc++.so.6()(64bit)
Requires:       libudev.so.1()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       xdg-utils
ExclusiveArch:  x86_64

%description
Obsidian is a powerful knowledge base that works on top of a local folder
of plain text Markdown files. The human brain is non-linear: we jump from
idea to idea, all the time. Your second brain should work the same.

%prep
%setup -q -c -T
APPIMAGE="%{SOURCE0}"
OFFSET=$(LC_ALL=C readelf -h "$APPIMAGE" | awk 'NR==13{e_shoff=$5} NR==18{e_shentsize=$5} NR==19{e_shnum=$5} END{print e_shoff+e_shentsize*e_shnum}')
unsquashfs -q -d squashfs-root -o "$OFFSET" "$APPIMAGE"
chmod go-w squashfs-root

%build

%install
install -dm755 %{buildroot}/opt/obsidian
cp -ar squashfs-root/* %{buildroot}/opt/obsidian/
if [ -f "%{buildroot}/opt/obsidian/chrome-sandbox" ]; then
    chmod 4755 %{buildroot}/opt/obsidian/chrome-sandbox
fi

install -Dm755 %{SOURCE2} %{buildroot}%{_bindir}/%{name}

install -dm755 %{buildroot}%{_datadir}/applications
sed -e 's|^Exec=.*|Exec=%{_bindir}/obsidian %U|' -e 's|^Icon=.*|Icon=%{app_id}|' \
    squashfs-root/%{app_id}.desktop > %{buildroot}%{_datadir}/applications/%{app_id}.desktop

for sizedir in squashfs-root/%{_datadir}/icons/hicolor/[0-9]*x[0-9]*/apps; do
    [ -f "$sizedir/obsidian.png" ] || continue
    sz=$(basename "$(dirname "$sizedir")")
    install -Dm644 "$sizedir/obsidian.png" \
        "%{buildroot}%{_datadir}/icons/hicolor/$sz/apps/%{app_id}.png"
done
install -Dm644 squashfs-root/obsidian.png %{buildroot}%{_datadir}/pixmaps/%{app_id}.png

install -Dm644 squashfs-root/%{_datadir}/mime/packages/obsidian.xml \
    %{buildroot}%{_datadir}/mime/packages/obsidian.xml

%fdupes %{buildroot}/opt/obsidian

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{app_id}.desktop

%files
%license /opt/obsidian/LICENSE.electron.txt
%doc /opt/obsidian/LICENSES.chromium.html
%{_bindir}/%{name}
%{_datadir}/applications/%{app_id}.desktop
%{_datadir}/icons/hicolor/*/apps/%{app_id}.png
%{_datadir}/pixmaps/%{app_id}.png
%{_datadir}/mime/packages/obsidian.xml
%exclude /opt/obsidian/LICENSE.electron.txt
%exclude /opt/obsidian/LICENSES.chromium.html
%exclude /opt/obsidian/AppRun
/opt/obsidian/
%exclude /opt/obsidian/chrome-sandbox
%attr(4755, root, root) /opt/obsidian/chrome-sandbox

%changelog
