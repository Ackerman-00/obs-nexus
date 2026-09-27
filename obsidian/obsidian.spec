%global app_id md.obsidian.Obsidian
%global debug_package %{nil}
# Bundled Electron runtime inside /opt/obsidian - exclude its private libs
# from automatic dependency generation (same pattern as fluxer/vesktop).
%global __requires_exclude_from ^/opt/obsidian/.*$
%global __provides_exclude_from ^/opt/obsidian/.*$
Name:           obsidian
Version:        1.13.7
Release:        0
# Shortened to pass the 79-character RPMLINT limit
Summary:        A powerful knowledge base for plain text Markdown files
# OpenSUSE requires this exact string for proprietary software
License:        NonFree
Group:          Productivity/Text/Editors
URL:            https://obsidian.md/
# Upstream ships self-contained AppImages (bundled Electron) per arch.
# update.sh guards: if a release has no Linux AppImage assets (e.g. v1.13.8
# was APK-only), the release is skipped and the spec stays on the last good
# Linux version.
Source0:        Obsidian-%{version}.AppImage
Source1:        Obsidian-%{version}-arm64.AppImage
# The custom wrapper script launching the bundled Electron binary
Source2:        obsidian.sh
Source3:        obsidian-rpmlintrc
BuildRequires:  binutils
BuildRequires:  desktop-file-utils
BuildRequires:  fdupes
BuildRequires:  hicolor-icon-theme
BuildRequires:  squashfs
Requires:       bash
# Runtime dependencies for the bundled Electron/Chromium runtime (soname
# form where possible so TW/Slowroll resolve identically; no longer uses
# the distro `electron` provider - fixes issue #9 where nodejs-electron
# required libabsl sonames nothing provides).
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
ExclusiveArch:  x86_64 aarch64

%description
Obsidian is a powerful knowledge base that works on top of a local folder
of plain text Markdown files. The human brain is non-linear: we jump from
idea to idea, all the time. Your second brain should work the same.

%prep
# Unpack the arch-appropriate AppImage (bundled Electron, no system
# electron needed). Offset via ELF section headers (same as rootapp).
%setup -q -c -T
%ifarch x86_64
APPIMAGE="%{SOURCE0}"
%endif
%ifarch aarch64
APPIMAGE="%{SOURCE1}"
%endif
OFFSET=$(LC_ALL=C readelf -h "$APPIMAGE" | awk 'NR==13{e_shoff=$5} NR==18{e_shentsize=$5} NR==19{e_shnum=$5} END{print e_shoff+e_shentsize*e_shnum}')
unsquashfs -q -d squashfs-root -o "$OFFSET" "$APPIMAGE"
chmod go-w squashfs-root

%build
# Nothing to compile.

%install
# 1. Install the bundled app (Electron binary + resources) to /opt
install -dm755 %{buildroot}/opt/obsidian
cp -ar squashfs-root/* %{buildroot}/opt/obsidian/
# Electron sandbox needs setuid like vesktop/stoat
if [ -f "%{buildroot}/opt/obsidian/chrome-sandbox" ]; then
    chmod 4755 %{buildroot}/opt/obsidian/chrome-sandbox
fi

# 2. Install the custom launcher script (bundled Electron + user flags)
install -Dm755 %{SOURCE2} %{buildroot}%{_bindir}/%{name}

# 3. Desktop entry from the AppImage, repointed at our wrapper + icon
install -dm755 %{buildroot}%{_datadir}/applications
sed -e 's|^Exec=.*|Exec=%{_bindir}/obsidian %U|' -e 's|^Icon=.*|Icon=%{app_id}|' \
    squashfs-root/%{app_id}.desktop > %{buildroot}%{_datadir}/applications/%{app_id}.desktop

# 4. Icon from the AppImage
install -Dm644 squashfs-root/obsidian.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/%{app_id}.png
install -Dm644 squashfs-root/obsidian.png %{buildroot}%{_datadir}/pixmaps/%{app_id}.png

# OpenSUSE optimization: hardlink duplicate files
%fdupes %{buildroot}/opt/obsidian

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/%{app_id}.desktop

%files
%license /opt/obsidian/LICENSE.electron.txt
%doc /opt/obsidian/LICENSES.chromium.html
%{_bindir}/%{name}
%{_datadir}/applications/%{app_id}.desktop
%{_datadir}/icons/hicolor/256x256/apps/%{app_id}.png
%{_datadir}/pixmaps/%{app_id}.png
%exclude /opt/obsidian/LICENSE.electron.txt
%exclude /opt/obsidian/LICENSES.chromium.html
# Unused AppImage runtime loader (we launch /opt/obsidian/obsidian
# directly via the wrapper script); excluded so its /usr/bin/env
# shebang does not trip env-script-interpreter.
%exclude /opt/obsidian/AppRun
/opt/obsidian/
%exclude /opt/obsidian/chrome-sandbox
%attr(4755, root, root) /opt/obsidian/chrome-sandbox

%changelog
