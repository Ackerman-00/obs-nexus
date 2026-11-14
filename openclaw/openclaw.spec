%global __requires_exclude_from ^/usr/lib/OpenClaw/desktop-runtime/bin/bun$
%global __provides_exclude_from ^/usr/lib/OpenClaw/desktop-runtime/bin/bun$
%global debug_package %{nil}

Name:           openclaw
Version:        2026.11.2
Release:        0
Summary:        Your AI assistant, running on your own devices and chats
License:        MIT
Group:          Applications/Utility
URL:            https://github.com/openclaw/openclaw
Source0:        %{url}/releases/download/v%{version}/OpenClaw-%{version}-amd64.deb
# sha256:  190d8990e78caf36ef03089a43477897f75932f53287c8cd14a8f9cdd9eda5cb
Source1:        openclaw-rpmlintrc
Source2:        openclaw-LICENSE
ExclusiveArch:  x86_64

BuildRequires:  binutils
BuildRequires:  tar
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme

Requires:       libgtk-3.so.0()(64bit)
Requires:       libwebkit2gtk-4.1.so.0()(64bit)
Requires:       libjavascriptcoregtk-4.1.so.0()(64bit)
Requires:       libsoup-3.0.so.0()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgdk-3.so.0()(64bit)
Requires:       libgdk_pixbuf-2.0.so.0()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libX11.so.6()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libayatana-appindicator3.so.1()(64bit)
Requires:       gstreamer-plugins-good
Requires:       gstreamer-plugins-bad
Requires:       gstreamer-plugins-libav
Recommends:     xdg-desktop-portal
Recommends:     xdg-desktop-portal-gtk

%description
OpenClaw is an open-source personal AI assistant that runs on your own computer
and answers in the chats you already use. This package ships the upstream
prebuilt Linux companion app (a GTK3/WebKitGTK window plus the bundled Bun
runtime). It repackages the upstream DEB payload as-is; it does not build
anything from source and cannot update itself.

%prep
%setup -q -c -T
ar x %{SOURCE0}
tar xzf data.tar.gz || { echo "ERROR: unexpected data.tar compression in upstream DEB" >&2; exit 1; }

%build

%install
install -d -m 0755 %{buildroot}%{_prefix}/lib/OpenClaw
cp -a usr/lib/OpenClaw/desktop-runtime %{buildroot}%{_prefix}/lib/OpenClaw/
install -Dpm0755 usr/lib/OpenClaw/install-cli.sh %{buildroot}%{_prefix}/lib/OpenClaw/install-cli.sh
install -Dpm0755 usr/bin/openclaw-desktop %{buildroot}%{_bindir}/openclaw-desktop
sed -i '1s|^#!/usr/bin/env bash$|#!/usr/bin/bash|' %{buildroot}%{_prefix}/lib/OpenClaw/install-cli.sh

install -d %{buildroot}%{_datadir}/icons/hicolor
for d in usr/share/icons/hicolor/*/apps/openclaw-desktop.png; do
    size=$(echo "$d" | cut -d/ -f5)
    install -Dpm0644 "$d" %{buildroot}%{_datadir}/icons/hicolor/${size}/apps/openclaw-desktop.png
done

install -d %{buildroot}%{_datadir}/applications
install -Dpm0644 usr/share/applications/OpenClaw.desktop %{buildroot}%{_datadir}/applications/OpenClaw.desktop
install -Dpm0644 %{SOURCE2} %{buildroot}%{_prefix}/lib/OpenClaw/LICENSE

find %{buildroot} \( -path '*/resources/app-update.yml' -o -path '*/resources/package-type' \) -delete 2>/dev/null || true
%check
desktop-file-validate %{buildroot}%{_datadir}/applications/OpenClaw.desktop

%files
%license %{_prefix}/lib/OpenClaw/LICENSE
%{_bindir}/openclaw-desktop
%{_prefix}/lib/OpenClaw/
%{_datadir}/applications/OpenClaw.desktop
%dir %{_datadir}/icons/hicolor/*
%dir %{_datadir}/icons/hicolor/*/apps
%{_datadir}/icons/hicolor/*/apps/openclaw-desktop.png

%post
if command -v update-mime-database >/dev/null 2>&1; then update-mime-database %{_datadir}/mime >/dev/null 2>&1 || true; fi
if command -v update-desktop-database >/dev/null 2>&1; then update-desktop-database %{_datadir}/applications >/dev/null 2>&1 || true; fi

%changelog
