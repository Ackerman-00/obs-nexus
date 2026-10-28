%global debug_package %{nil}
%global __requires_exclude_from ^/opt/hyperframes/.*$
%global __provides_exclude_from ^/opt/hyperframes/.*$
Name:           hyperframes-desktop
Version:        0.1.0.b520
# sha256:  994a190439777d2f62888863bc60154003eda747b4bfee70b59b2c6de1a0f91b
Release:        0
Summary:        HyperFrames Studio (Electron)
License:        Apache-2.0 AND MIT AND BSD-3-Clause
Group:          Productivity/Multimedia/Video/Editors and Convertors
URL:            https://hyperframes.dev
Source0:        https://static.heygen.ai/hyperframes-oss/desktop/HyperFrames-amd64.deb
Source1:        hyperframes-desktop-rpmlintrc
BuildRequires:  binutils
BuildRequires:  desktop-file-utils
BuildRequires:  tar
BuildRequires:  zstd
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
Recommends:     xdg-desktop-portal
Recommends:     xdg-desktop-portal-gtk
ExclusiveArch:  x86_64

%description
HyperFrames Studio re-packs the upstream .deb payload under /opt.

%prep
%setup -q -c -T
ar x %{SOURCE0}
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
if [ -L usr/bin/hyperframes ] || [ -e usr/bin/hyperframes ]; then ln -sf /opt/hyperframes/HyperFrames %{buildroot}%{_bindir}/hyperframes; fi

%files
/opt/hyperframes/
%{_bindir}/hyperframes
%{_datadir}/applications/*
%{_datadir}/pixmaps/*

%post
if command -v update-mime-database >/dev/null 2>&1; then update-mime-database %{_datadir}/mime >/dev/null 2>&1 || true; fi
if command -v update-desktop-database >/dev/null 2>&1; then update-desktop-database %{_datadir}/applications >/dev/null 2>&1 || true; fi
if ! { [ -L /proc/self/ns/user ] && unshare --user true; }; then
  chmod 4755 /opt/hyperframes/chrome-sandbox || true
else
  chmod 0755 /opt/hyperframes/chrome-sandbox || true
fi
if [ -f %{apparmor_profilesdir}/abi/4.0 ] && [ -x /sbin/apparmor_parser ] && [ -f /opt/hyperframes/apparmor.d/hyperframes ]; then
  cp -f /opt/hyperframes/apparmor.d/hyperframes %{apparmor_profilesdir}/hyperframes
  /sbin/apparmor_parser -r %{apparmor_profilesdir}/hyperframes >/dev/null 2>&1 || true
fi

%postun
if [ "$1" = 0 ] && [ -f %{apparmor_profilesdir}/hyperframes ]; then
  [ -x /sbin/apparmor_parser ] && /sbin/apparmor_parser -R %{apparmor_profilesdir}/hyperframes >/dev/null 2>&1 || true
  rm -f %{apparmor_profilesdir}/hyperframes
fi

%changelog
