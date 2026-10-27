%global debug_package %{nil}
%global __requires_exclude_from ^/opt/Freebuff/.*$
%global __provides_exclude_from ^/opt/Freebuff/.*$
Name:           freebuff-desktop
Version:        0.0.192
# sha256:  4fc4d1985dcb47e983fc67269e9bfd3ed63dde786931207a0f414c4aea836211
Release:        0
Summary:        Freebuff Desktop (Electron)
License:        SUSE-Freeware
Group:          Development/Tools/IDE
URL:            https://freebuff.com
# Use the upstream DEB as our raw source payload
Source0:        https://github.com/CodebuffAI/codebuff-community/releases/download/freebuff-desktop-v%{version}/Freebuff-%{version}-linux-amd64.deb
Source1:        freebuff-desktop-rpmlintrc
BuildRequires:  binutils
BuildRequires:  tar
BuildRequires:  zstd
BuildRequires:  desktop-file-utils
# a11y bus daemon: Electron's AT-SPI path needs it at runtime (matches the
# proven omnirush/hyperframes Requires set)
Requires:       at-spi2-core
# Hand-mapped soname Depends (Electron runtime, same as freebuff .deb)
Requires:       libasound.so.2()(64bit)
Requires:       libatk-1.0.so.0()(64bit)
Requires:       libatk-bridge-2.0.so.0()(64bit)
Requires:       libatspi.so.0()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libcups.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libdrm.so.2()(64bit)
Requires:       libexpat.so.1()(64bit)
Requires:       libgcc_s.so.1()(64bit)
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
# dlopen-only at runtime (not DT_NEEDED, invisible to auto-deps): libpulse
# for audio playback, libpipewire for capture, libsecret for OS-keyring
# credential storage - proven by strings in the shipped freebuff main
# binary (4/11/7 hits; same Chromium code path as omnirush/hyperframes).
# libnotify above is the same strings-proven dlopen (7 hits) and mirrors
# the upstream .deb's libnotify4.
Requires:       libpipewire-0.3.so.0()(64bit)
Requires:       libpulse.so.0()(64bit)
Requires:       libsecret-1.so.0()(64bit)
Requires:       libsmime3.so()(64bit)
Requires:       libstdc++.so.6()(64bit)
Requires:       libudev.so.1()(64bit)
Requires:       libX11.so.6()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libXcomposite.so.1()(64bit)
Requires:       libXdamage.so.1()(64bit)
Requires:       libXext.so.6()(64bit)
Requires:       libXfixes.so.3()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       libXrandr.so.2()(64bit)
# DT_NEEDED of the bundled git under resources/git (git -> libz.so.1,
# git-remote-http -> libcurl.so.4; readelf on the payload); both resolve on
# Tumbleweed (libz1 / libcurl4).
Requires:       libcurl.so.4()(64bit)
Requires:       libz.so.1()(64bit)
# Upstream .deb control parity (electron-builder stock Depends list).
# libuuid1/libxtst6 are referenced by no payload ELF (0 readelf/strings
# hits) but upstream declares them and our debian.control carries them, so
# keep the RPM side in step. xdg-utils IS referenced (xdg-open, 2 strings).
# libXScrnSaver is deliberately NOT required on the RPM side: Tumbleweed
# ships no provider at all (zypper search --provides libXScrnSaver.so.1:
# no matching items) and nothing in the payload references it; the Debian
# side keeps libxss1 where the archive does provide it.
Requires:       libuuid.so.1()(64bit)
Requires:       libXtst.so.6()(64bit)
Requires:       xdg-utils
Requires:       hicolor-icon-theme
ExclusiveArch:  x86_64

%description
Freebuff Desktop re-packs the upstream .deb payload under /opt.

%prep
%setup -q -c -T
ar x %{SOURCE0}
if [ -f data.tar.xz ]; then tar xf data.tar.xz
elif [ -f data.tar.zst ]; then tar --zstd -xf data.tar.zst
elif [ -f data.tar.gz ]; then tar xzf data.tar.gz
else echo "ERROR: unexpected data.tar compression in upstream DEB" >&2; exit 1; fi

%build
:

%install
install -d %{buildroot}/opt %{buildroot}%{_datadir} %{buildroot}%{_bindir}
if [ -d opt/Freebuff ]; then cp -a opt/Freebuff %{buildroot}/opt/; fi
if [ -d usr/share ]; then cp -a usr/share/* %{buildroot}%{_datadir}/; fi
if [ -d usr/share/applications ]; then install -d %{buildroot}%{_datadir}/applications; fi
# plain symlink (see freebuff package rationale in post): single provider
ln -sf /opt/Freebuff/freebuff %{buildroot}%{_bindir}/freebuff

%files
/opt/Freebuff/
%{_bindir}/freebuff
%{_datadir}/applications/*
# upstream ships usr/share/doc/freebuff/changelog.gz; without this entry
# rpmbuild dies "Installed (but unpackaged) file(s) found" (reproduced on
# OBS openSUSE_Tumbleweed 2026-10-27, same class as omnirush line 97)
%{_datadir}/doc/freebuff/
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/*
%dir %{_datadir}/icons/hicolor/*/apps
%{_datadir}/icons/hicolor/*/*/freebuff.png

%changelog
