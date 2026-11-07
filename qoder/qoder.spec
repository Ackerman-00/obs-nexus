%global debug_package %{nil}
%global __requires_exclude_from ^/opt/Qoder/.*$
%global __provides_exclude_from ^/opt/Qoder/.*$
Name:           qoder
Version:        0.5.6
# sha256: 0058d5ff97b71c1e97935595fdcb07613bd20e9d7ba7f672c9efc7b566fc40d4
Release:        0
Epoch:          1
Summary:        Agent workbench for human and AI software teams
License:        SUSE-Freeware
Group:          Development/Tools/IDE
URL:            https://qoder.com
Source0:        https://download.qoder.com.cn/qoder-app/releases/0.5.6/Qoder-linux-amd64.deb
Source1:        qoder-rpmlintrc
BuildRequires:  binutils
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
BuildRequires:  tar
Requires:       at-spi2-core
Requires:       hicolor-icon-theme
Requires:       xdg-utils
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
Requires:       libnspr4.so()(64bit)
Requires:       libnss3.so()(64bit)
Requires:       libnssutil3.so()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
Requires:       libsecret-1.so.0()(64bit)
Requires:       libsmime3.so()(64bit)
Requires:       libstdc++.so.6()(64bit)
Requires:       libudev.so.1()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       libX11-xcb.so.1()(64bit)
Requires:       libXcursor.so.1()(64bit)
Requires:       libnotify.so.4()(64bit)
Requires:       libpipewire-0.3.so.0()(64bit)
Requires:       libpulse.so.0()(64bit)
ExclusiveArch:  x86_64

%description
Qoder is an agent workbench for human and AI software teams. It packages the
upstream Electron 43 (Chromium 150) desktop client, the Qoder agent SDK, and
the collaboration CLI for Linux x86_64.

This RPM re-packs the upstream .deb payload under /opt/Qoder without changing
it, so the app keeps its own update feed (electron-updater, generic provider at
https://download.qoder.com.cn/qoder-app/releases).

%prep
%setup -q -c -T

ar x %{SOURCE0}
if [ -f data.tar.xz ]; then
  tar xf data.tar.xz
elif [ -f data.tar.gz ]; then
  tar xzf data.tar.gz
elif [ -f data.tar.zst ]; then
  tar --zstd -xf data.tar.zst
else
  echo "ERROR: unexpected data.tar compression in upstream DEB" >&2
  exit 1
fi

%build

%install
install -d -m 0755 %{buildroot}/opt
cp -a opt/Qoder %{buildroot}/opt/

install -d -m 0755 %{buildroot}%{_bindir}
ln -sf /opt/Qoder/qoder %{buildroot}%{_bindir}/qoder

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
install -d -m 0755 %{buildroot}%{_docdir}/qoder
cp -a usr/share/doc/qoder/. %{buildroot}%{_docdir}/qoder/

chmod 4755 %{buildroot}/opt/Qoder/chrome-sandbox

desktop-file-validate %{buildroot}%{_datadir}/applications/qoder.desktop

%post
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database %{_datadir}/applications >/dev/null 2>&1 || true
fi
if command -v update-mime-database >/dev/null 2>&1; then
  update-mime-database %{_datadir}/mime >/dev/null 2>&1 || true
fi
if [ -d %{_sysconfdir}/apparmor.d ] && [ -x /sbin/apparmor_parser ] \
   && [ -f /opt/Qoder/resources/apparmor-profile ]; then
  if /sbin/apparmor_parser --skip-kernel-load --debug \
       /opt/Qoder/resources/apparmor-profile >/dev/null 2>&1; then
    install -m 0644 /opt/Qoder/resources/apparmor-profile \
      %{_sysconfdir}/apparmor.d/qoder
    /sbin/apparmor_parser --replace --write-cache --skip-read-cache \
      %{_sysconfdir}/apparmor.d/qoder >/dev/null 2>&1 || true
  fi
fi

%postun
if [ "$1" = 0 ] && [ -f %{_sysconfdir}/apparmor.d/qoder ]; then
  if [ -x /sbin/apparmor_parser ]; then
    /sbin/apparmor_parser --remove %{_sysconfdir}/apparmor.d/qoder >/dev/null 2>&1 || true
  fi
  rm -f %{_sysconfdir}/apparmor.d/qoder
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database %{_datadir}/applications >/dev/null 2>&1 || true
fi

%files
%license /opt/Qoder/LICENSE.electron.txt
%license /opt/Qoder/LICENSES.chromium.html
%{_bindir}/qoder
%{_datadir}/applications/qoder.desktop
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/*
%dir %{_datadir}/icons/hicolor/*/apps
%{_datadir}/icons/hicolor/*/apps/qoder.png
%dir %{_docdir}/qoder
%doc %{_docdir}/qoder/changelog.gz
%dir /opt/Qoder
%exclude /opt/Qoder/chrome-sandbox
%exclude /opt/Qoder/LICENSE.electron.txt
%exclude /opt/Qoder/LICENSES.chromium.html
%attr(4755, root, root) /opt/Qoder/chrome-sandbox
/opt/Qoder/*

%changelog
