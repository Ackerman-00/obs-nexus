%global debug_package %{nil}
%global __requires_exclude_from ^/opt/hyperframes/.*$
%global __provides_exclude_from ^/opt/hyperframes/.*$
Name:           hyperframes-desktop
Version:        0.1.0.b496
# sha256:  a18bd06e77a875ee6f09f2f8bb44587f4a1c2d29d913ef4eaf37217d42f9891b
Release:        0
Summary:        HyperFrames Studio (Electron)
License:        Apache-2.0 AND MIT AND BSD-3-Clause
Group:          Productivity/Multimedia/Video/Editors and Convertors
URL:            https://hyperframes.dev
# Use the upstream DEB as our raw source payload
Source0:        https://static.heygen.ai/hyperframes-oss/desktop/HyperFrames-amd64.deb
Source1:        hyperframes-desktop-rpmlintrc
BuildRequires:  binutils
BuildRequires:  tar
BuildRequires:  zstd
BuildRequires:  desktop-file-utils
# a11y bus daemon: Electron's AT-SPI path needs it at runtime (matches the
# proven fluxer/obsidian Requires set)
Requires:       at-spi2-core
# Hand-mapped soname Depends (Electron runtime)
Requires:       libasound.so.2()(64bit)
Requires:       libatk-1.0.so.0()(64bit)
Requires:       libatk-bridge-2.0.so.0()(64bit)
Requires:       libatspi.so.0()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libcups.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
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
# credential storage - proven by strings in the shipped HyperFrames main
# binary (2/1/2 hits; same Chromium code path as fluxer/obsidian).
# libnotify above is the same strings-proven dlopen (1 hit).
# libsmime3 IS DT_NEEDED (was missing here).
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
Requires:       hicolor-icon-theme
ExclusiveArch:  x86_64

%description
HyperFrames Studio re-packs the upstream .deb payload under /opt.

%prep
%setup -q -c -T
ar x %{SOURCE0}
# guard every common data.tar compression (the static heygen URL is a
# rolling target; the current asset ships data.tar.xz)
if [ -f data.tar.gz ]; then tar xzf data.tar.gz
elif [ -f data.tar.xz ]; then tar xf data.tar.xz
elif [ -f data.tar.zst ]; then tar --zstd -xf data.tar.zst
else echo "ERROR: unexpected data.tar compression" >&2; exit 1; fi

%build
:

%install
install -d %{buildroot}/opt %{buildroot}%{_datadir} %{buildroot}%{_bindir} %{buildroot}%{_datadir}/applications
if [ -d opt/hyperframes ]; then cp -a opt/hyperframes %{buildroot}/opt/; fi
if [ -d usr/share ]; then cp -a usr/share/* %{buildroot}%{_datadir}/; fi
# usr/bin/hyperframes is a symlink to /opt/hyperframes/HyperFrames upstream;
# keep it a symlink - a plain install would duplicate the ~200 MB binary.
# Test with -L: the absolute symlink is dangling inside the buildroot
# (its /opt target only exists on the user's system), so -f/-e are false.
if [ -L usr/bin/hyperframes ] || [ -e usr/bin/hyperframes ]; then ln -sf /opt/hyperframes/HyperFrames %{buildroot}%{_bindir}/hyperframes; fi

%files
/opt/hyperframes/
%{_bindir}/hyperframes
%{_datadir}/applications/*
%{_datadir}/pixmaps/*

%post
if command -v update-mime-database >/dev/null 2>&1; then update-mime-database /usr/share/mime >/dev/null 2>&1 || true; fi
if command -v update-desktop-database >/dev/null 2>&1; then update-desktop-database /usr/share/applications >/dev/null 2>&1 || true; fi
if ! { [ -L /proc/self/ns/user ] && unshare --user true; }; then
  chmod 4755 /opt/hyperframes/chrome-sandbox || true
else
  chmod 0755 /opt/hyperframes/chrome-sandbox || true
fi
if [ -f /etc/apparmor.d/abi/4.0 ] && [ -x /sbin/apparmor_parser ] && [ -f /opt/hyperframes/apparmor.d/hyperframes ]; then
  cp -f /opt/hyperframes/apparmor.d/hyperframes /etc/apparmor.d/hyperframes
  /sbin/apparmor_parser -r /etc/apparmor.d/hyperframes >/dev/null 2>&1 || true
fi

%postun
if [ "$1" = 0 ] && [ -f /etc/apparmor.d/hyperframes ]; then
  [ -x /sbin/apparmor_parser ] && /sbin/apparmor_parser -R /etc/apparmor.d/hyperframes >/dev/null 2>&1 || true
  rm -f /etc/apparmor.d/hyperframes
fi

%changelog
