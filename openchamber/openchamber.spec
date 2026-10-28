%global debug_package %{nil}
%global __os_install_post %{nil}
%global __requires_exclude_from ^/opt/openchamber/.*$
%global __provides_exclude_from ^/opt/openchamber/.*$
Name:           openchamber
Version:        2.5.2
Release:        0
Summary:        Agentic development environment boards for issues and pull requests
License:        MIT
URL:            https://github.com/openchamber/openchamber
Source0:        https://github.com/openchamber/openchamber/releases/download/v%{version}/OpenChamber-%{version}-linux-x86_64.AppImage
BuildRequires:  desktop-file-utils
BuildRequires:  fdupes
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
Requires:       libdbusmenu-glib.so.4()(64bit)
Requires:       libexpat.so.1()(64bit)
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
Requires:       libutil.so.1()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       xdg-utils
ExclusiveArch:  x86_64

%description
OpenChamber is an agentic development environment based on the OpenCode AI
agent, with boards for GitHub/GitLab issues and pull requests, environment
variable management, and desktop builds for Linux.

%prep
%setup -q -c -T
chmod +x %{SOURCE0}
%{SOURCE0} --appimage-extract
chmod go-w squashfs-root

%build

%install
install -dm755 %{buildroot}/opt/openchamber
cp -ar squashfs-root/* %{buildroot}/opt/openchamber/

chmod 0755 %{buildroot}/opt/openchamber/chrome-sandbox

install -dm755 %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/openchamber <<'WRAPPER_EOF'
#!/bin/sh
export APPDIR="/opt/openchamber"
exec /opt/openchamber/AppRun "$@"
WRAPPER_EOF
chmod 755 %{buildroot}%{_bindir}/openchamber

install -dm755 %{buildroot}%{_datadir}/applications/
sed -e 's|^Exec=.*|Exec=%{_bindir}/openchamber %U|' -e 's|^Icon=.*|Icon=openchamber|' \
    squashfs-root/openchamber.desktop > %{buildroot}%{_datadir}/applications/openchamber.desktop

install -Dm644 squashfs-root/openchamber.png %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/openchamber.png

%fdupes %{buildroot}/opt/openchamber

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/openchamber.desktop

%files
%license /opt/openchamber/LICENSE.electron.txt
%doc /opt/openchamber/LICENSES.chromium.html
%{_bindir}/openchamber
%{_datadir}/applications/openchamber.desktop
%{_datadir}/icons/hicolor/256x256/apps/openchamber.png
%exclude /opt/openchamber/LICENSE.electron.txt
%exclude /opt/openchamber/LICENSES.chromium.html
/opt/openchamber/

%changelog
