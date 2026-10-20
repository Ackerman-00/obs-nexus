%global debug_package %{nil}
# Bundled prebuilt CEF runtime under /opt/koharu is immutable upstream
# binaries - exclude its private libs from auto-deps (repo convention,
# same as vesktop/obsidian/stoat-desktop).
%global __requires_exclude_from ^/opt/koharu/.*$
%global __provides_exclude_from ^/opt/koharu/.*$
Name:           koharu
Version:        0.83.5
Release:        0
Summary:        Local-first ML-powered manga translator
License:        MIT OR Apache-2.0
Group:          Productivity/Graphics/Other
URL:            https://github.com/koharu-rs/koharu
# Use the upstream DEB as our raw source payload (tags carry no v prefix)
Source0:        %{url}/releases/download/0.83.5/koharu_0.83.5_amd64.deb
Source1:        koharu-rpmlintrc
# Required to unpack the upstream DEB natively
BuildRequires:  binutils
BuildRequires:  fdupes
BuildRequires:  hicolor-icon-theme
BuildRequires:  tar
# Explicit dependencies mapped from the payload's ELF DT_NEEDED union
# (koharu binary wants gtk4/graphene/openssl; libcef.so wants the usual
# Chromium set; upstream's own Depends names only libgtk-3-0)
Requires:       at-spi2-core
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
Requires:       libcrypto.so.3()(64bit)
Requires:       libcups.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libexpat.so.1()(64bit)
Requires:       libfontconfig.so.1()(64bit)
Requires:       libgbm.so.1()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libgdk_pixbuf-2.0.so.0()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgraphene-1.0.so.0()(64bit)
Requires:       libgtk-4.so.1()(64bit)
Requires:       libnspr4.so()(64bit)
Requires:       libnss3.so()(64bit)
Requires:       libnssutil3.so()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
Requires:       libsmime3.so()(64bit)
Requires:       libssl.so.3()(64bit)
Requires:       libstdc++.so.6()(64bit)
Requires:       libudev.so.1()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       xdg-utils
ExclusiveArch:  x86_64

%description
Koharu is a local-first, ML-powered manga translator (speech-bubble
detection, OCR, inpainting, LLM translation) as a desktop app.
This version natively extracts the upstream DEB payload.

%prep
%setup -q -c -T
# Rip open the upstream DEB natively (Tauri bundler ships data.tar.gz)
ar x %{SOURCE0}
if [ -f data.tar.gz ]; then
  tar xzf data.tar.gz
else
  echo "ERROR: unexpected data.tar compression in upstream DEB" >&2
  exit 1
fi

%build
# No compilation required for pre-built binaries

%install

# Install the CEF application bundle under /opt (repo convention for
# prebuilt Electron/CEF apps: vesktop/obsidian/stoat-desktop). /usr/share
# is reserved for arch-independent files - ELFs there trip rpmlint
# E: arch-dependent-file-in-usr-share and abort the OBS build (badness).
# The whole directory moves together, so the binary's relative resource
# lookup (locales, .pak, libcef.so) keeps working.
install -d -m 0755 %{buildroot}/opt/koharu
cp -a usr/share/koharu/* %{buildroot}/opt/koharu/
# Upstream stashes the license texts under usr/lib/koharu/_up_; keep them
# with the bundle and mark them as license files below.
cp -a usr/lib/koharu/_up_/_up_/LICENSE-MIT usr/lib/koharu/_up_/_up_/LICENSE-APACHE %{buildroot}/opt/koharu/
# Launcher symlink (replaces upstream's usr/bin/koharu -> ../share/... link,
# which no longer resolves after the move to /opt).
install -d -m 0755 %{buildroot}%{_bindir}
ln -s ../../opt/koharu/koharu %{buildroot}%{_bindir}/koharu
# Desktop entry + icons, byte-for-byte from the payload.
install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
# Deduplicate the near-identical en-US_*.pak locale files.
%fdupes %{buildroot}/opt/koharu

%files
%license /opt/koharu/LICENSE-MIT
%license /opt/koharu/LICENSE-APACHE
%{_bindir}/koharu
%{_datadir}/applications/koharu.desktop
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/*
%dir %{_datadir}/icons/hicolor/*/apps
%{_datadir}/icons/hicolor/*/apps/koharu.png
%dir /opt/koharu
%exclude /opt/koharu/chrome-sandbox
%exclude /opt/koharu/LICENSE-MIT
%exclude /opt/koharu/LICENSE-APACHE
/opt/koharu/*
%attr(4755, root, root) /opt/koharu/chrome-sandbox

%changelog
