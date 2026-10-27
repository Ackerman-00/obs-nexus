%global debug_package %{nil}
Name:           cline-desktop
Version:        0.0.49
# sha256:  3e2c1f824fbdceaf67a8c01404e58218f8534f952318d1689807824b9ca2e2f6
Release:        0
Summary:        The agentic coding-capable IDE desktop app (Tauri)
License:        Apache-2.0
Group:          Development/Tools/IDE
URL:            https://cline.bot
# Use the upstream DEB as our raw source payload
Source0:        https://github.com/cline/cline/releases/download/desktop-v0.0.49/Cline_0.0.49_amd64.deb
Source1:        cline-desktop-rpmlintrc
# Required to unpack the upstream DEB natively
BuildRequires:  binutils
BuildRequires:  tar
BuildRequires:  zstd
# Hand-mapped soname Depends; auto-Requires are off implicitly through
# the /usr layout? Cline ships under /usr/lib/Cline and /usr/bin; keep
# the explicit set so zypper finds a desktop runtime on Tumbleweed even
# before a rebuild. Mirror of the upstream .deb's Depends, plus the
# WebKit/GTK runtime cline-app DT_NEEDEDs (auto-deps cover /usr paths).
Requires:       libgtk-3.so.0()(64bit)
Requires:       libgdk-3.so.0()(64bit)
Requires:       libgdk_pixbuf-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libjavascriptcoregtk-4.1.so.0()(64bit)
Requires:       libsoup-3.0.so.0()(64bit)
Requires:       libwebkit2gtk-4.1.so.0()(64bit)
# Tray icon: cline-app dlopens libayatana-appindicator3.so.1 /
# libappindicator3.so.1 at runtime (46 libappindicator strings + the
# "Failed to load ayatana-appindicator3 or appindicator3 dynamic library"
# message in the shipped binary; mirrors the upstream .deb's Depends on
# libayatana-appindicator3-1). dlopen-only, so invisible to auto-deps.
Requires:       libayatana-appindicator3-1
Requires:       hicolor-icon-theme
ExclusiveArch:  x86_64

%description
Cline desktop (the agentic coding assistant) ships the upstream DEB payload
as-is: /usr/lib/Cline (Tauri binary bundle), /usr/bin/cline-app and
cline-cli, and the desktop/metainfo/icons in /usr/share. This spec re-packs
those bytes without recompiling.

%prep
%setup -q -c -T
ar x %{SOURCE0}
# desktop-v0.0.49 ships data.tar.gz; guard every common compression so an
# upstream packaging change cannot silently break the re-pack build.
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
# nothing to compile

%install
install -d %{buildroot}%{_datadir} %{buildroot}/usr/lib %{buildroot}%{_bindir}
cp -a usr/share/* %{buildroot}%{_datadir}/
if [ -d usr/lib/Cline ]; then cp -a usr/lib/Cline %{buildroot}/usr/lib/; fi
for b in usr/bin/*; do install -m 0755 "$b" %{buildroot}%{_bindir}/; done

%files
%{_bindir}/cline-app
%{_bindir}/cline-cli
/usr/lib/Cline/
%{_datadir}/applications/*
%{_datadir}/icons/hicolor/*/apps/*
%{_datadir}/metainfo/*

%changelog

