%global debug_package %{nil}
%global __requires_exclude_from ^/opt/OpenChamber/.*$
%global __provides_exclude_from ^/opt/OpenChamber/.*$
Name:           openchamber
Version:        2.7.2
Release:        1
Summary:        Agentic development environment boards for issues and pull requests
License:        MIT
Group:          Development/Tools/IDE
URL:            https://github.com/openchamber/openchamber
Source0:        %{url}/releases/download/v%{version}/OpenChamber-%{version}-linux-amd64.deb
# sha256:  d991ee6ade4c203ff200c7314ff7e1f8ad50c6a1ddfd0d647a681cd1bd9aa28d
Source1:        openchamber-rpmlintrc
BuildRequires:  binutils
BuildRequires:  tar
BuildRequires:  zstd
BuildRequires:  xz
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
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
Requires:       libgbm.so.1()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libgdk_pixbuf-2.0.so.0()(64bit)
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
Recommends:     xdg-desktop-portal
Recommends:     xdg-desktop-portal-gtk
Recommends:     libayatana-appindicator3.so.1()(64bit)
ExclusiveArch:  x86_64

%description
OpenChamber is an agentic development environment based on the OpenCode AI
agent, with boards for GitHub/GitLab issues and pull requests, environment
variable management, and desktop builds for Linux.

%prep
%setup -q -c -T
ar x %{SOURCE0}
if [ -f data.tar.xz ]; then
  tar -xpf data.tar.xz
elif [ -f data.tar.zst ]; then
  tar --zstd -xpf data.tar.zst
elif [ -f data.tar.gz ]; then
  tar -xzf data.tar.gz
else
  echo "ERROR: unexpected data.tar compression in upstream DEB" >&2
  exit 1
fi

%build

%install
install -d -m 0755 %{buildroot}/opt
cp -a opt/OpenChamber %{buildroot}/opt/
find %{buildroot}/opt/OpenChamber -type f | xargs chmod go-w 2>/dev/null || true
chmod 0755 %{buildroot}/opt/OpenChamber/chrome-sandbox

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/ 2>/dev/null || true

desktop-file-validate %{buildroot}%{_datadir}/applications/openchamber.desktop
find %{buildroot} \( -path '*/resources/app-update.yml' -o -path '*/resources/package-type' \) -delete 2>/dev/null || true

%post
if ! { [ -L /proc/self/ns/user ] && unshare --user true; }; then
  chmod 4755 /opt/OpenChamber/chrome-sandbox || true
else
  chmod 0755 /opt/OpenChamber/chrome-sandbox || true
fi

%files
%license /opt/OpenChamber/LICENSE.electron.txt
%doc /opt/OpenChamber/LICENSES.chromium.html
%{_datadir}/applications/openchamber.desktop
%{_datadir}/icons/hicolor/512x512/apps/openchamber.png
%dir %{_datadir}/doc/openchamber
%doc %{_datadir}/doc/openchamber/changelog.gz
%dir /opt/OpenChamber
%exclude /opt/OpenChamber/chrome-sandbox
%exclude /opt/OpenChamber/LICENSE.electron.txt
%exclude /opt/OpenChamber/LICENSES.chromium.html
%attr(4755, root, root) /opt/OpenChamber/chrome-sandbox
/opt/OpenChamber/*

%changelog
* Sun Nov 15 2026 Ackerman-00 <no-reply> - 2.7.2-0
- Switch the RPM recipe from the AppImage payload to the native
  upstream .deb (OpenChamber-2.7.2-linux-amd64.deb), repacked the same
  way as qoder/cline-desktop; matches how the DEB recipe feeds off the
  same .deb. The upstream Electron runtime now installs flat under
  /opt/OpenChamber and the desktop entry execs it directly, so there
  is no /usr/bin/openchamber link - the openchamber name on PATH is the
  web CLI from @openchamber/web.
