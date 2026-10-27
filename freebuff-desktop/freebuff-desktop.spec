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
Source0:        https://github.com/CodebuffAI/codebuff-community/releases/download/freebuff-desktop-v%{version}/Freebuff-%{version}-linux-amd64.deb
Source1:        freebuff-desktop-rpmlintrc
BuildRequires:  binutils
BuildRequires:  tar
BuildRequires:  zstd
BuildRequires:  desktop-file-utils
Requires:       at-spi2-core
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
Requires:       libcurl.so.4()(64bit)
Requires:       libz.so.1()(64bit)
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
ln -sf /opt/Freebuff/freebuff %{buildroot}%{_bindir}/freebuff

%files
/opt/Freebuff/
%{_bindir}/freebuff
%{_datadir}/applications/*
%{_datadir}/doc/freebuff/
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/*
%dir %{_datadir}/icons/hicolor/*/apps
%{_datadir}/icons/hicolor/*/*/freebuff.png

%changelog
