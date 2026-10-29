%global debug_package %{nil}
%global __requires_exclude_from ^%{_prefix}/lib/Cline/bin/remote-helpers/
%global __provides_exclude_from ^%{_prefix}/lib/Cline/bin/remote-helpers/
Name:           cline-desktop
Version:        0.0.49
# sha256:  3e2c1f824fbdceaf67a8c01404e58218f8534f952318d1689807824b9ca2e2f6
Release:        0
Summary:        The agentic coding-capable IDE desktop app (Tauri)
License:        Apache-2.0
Group:          Development/Tools/IDE
URL:            https://cline.bot
Source0:        https://github.com/cline/cline/releases/download/desktop-v0.0.49/Cline_0.0.49_amd64.deb
Source1:        cline-desktop-rpmlintrc
BuildRequires:  binutils
BuildRequires:  tar
BuildRequires:  zstd
Requires:       hicolor-icon-theme
Requires:       libayatana-appindicator3.so.1()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libgdk-3.so.0()(64bit)
Requires:       libgdk_pixbuf-2.0.so.0()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgtk-3.so.0()(64bit)
Requires:       libjavascriptcoregtk-4.1.so.0()(64bit)
Requires:       libsoup-3.0.so.0()(64bit)
Requires:       libwebkit2gtk-4.1.so.0()(64bit)
Recommends:     xdg-desktop-portal
Recommends:     xdg-desktop-portal-gtk
ExclusiveArch:  x86_64

%description
Cline desktop (the agentic coding assistant) ships the upstream DEB payload
as-is: %{_prefix}/lib/Cline (Tauri binary bundle), %{_bindir}/cline-app and
cline-cli, and the desktop/metainfo/icons in %{_prefix}/share. This spec re-packs
those bytes without recompiling.

%prep
%setup -q -c -T
ar x %{SOURCE0}
if [ -f data.tar.gz ]; then
  tar xzf data.tar.gz
elif [ -f data.tar.xz ]; then
  tar xf data.tar.xz
elif [ -f data.tar.zst ]; then
  tar --zstd -xf data.tar.zst
else
  echo "ERROR: unexpected data.tar compression in upstream DEB" >&2
  exit 1
fi

%build

%install
install -d %{buildroot}%{_datadir} %{buildroot}%{_prefix}/lib %{buildroot}%{_bindir}
cp -a usr/share/* %{buildroot}%{_datadir}/
if [ -d usr/lib/Cline ]; then cp -a usr/lib/Cline %{buildroot}%{_prefix}/lib/; fi
for b in usr/bin/*; do install -m 0755 "$b" %{buildroot}%{_bindir}/; done

%files
%{_bindir}/cline-app
%{_bindir}/cline-cli
%{_prefix}/lib/Cline/
%{_datadir}/applications/*
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/*
%dir %{_datadir}/icons/hicolor/*/apps
%{_datadir}/icons/hicolor/*/apps/*
%{_datadir}/metainfo/*

%changelog
