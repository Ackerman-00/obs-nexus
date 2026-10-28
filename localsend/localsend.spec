%global debug_package %{nil}
%global __requires_exclude_from ^/opt/localsend_app/.*$
%global __provides_exclude_from ^/opt/localsend_app/.*$
Name:           localsend
Version:        1.18.2
Release:        0
Summary:        An open source cross-platform alternative to AirDrop
License:        GPL-3.0-only
Group:          Productivity/Networking/Other
URL:            https://github.com/localsend/localsend
Source0:        %{url}/releases/download/v1.18.2/LocalSend-1.18.2-linux-x86-64.deb
Source1:        localsend-rpmlintrc
BuildRequires:  binutils
BuildRequires:  tar
BuildRequires:  zstd
Requires:       libatk-1.0.so.0()(64bit)
Requires:       libayatana-appindicator3.so.1()(64bit)
Requires:       libayatana-ido3-0.4.so.0()(64bit)
Requires:       libayatana-indicator3.so.7()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libepoxy.so.0()(64bit)
Requires:       libfontconfig.so.1()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libgdk-3.so.0()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgtk-3.so.0()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
Requires:       libpangocairo-1.0.so.0()(64bit)
Requires:       libstdc++.so.6()(64bit)
Requires:       xdg-user-dirs
Recommends:     xdg-desktop-portal
Recommends:     xdg-desktop-portal-gtk
ExclusiveArch:  x86_64

%description
LocalSend is a free, open-source app that enables secure communication
between devices using a REST API and HTTPS encryption. Unlike other
messaging apps that rely on external servers, LocalSend doesn't require
an internet connection or third-party servers, making it a fast and
reliable solution for local communication.
This version natively extracts the upstream DEB payload.

%prep
%setup -q -c -T
ar x %{SOURCE0}
if [ -f data.tar.xz ]; then
  tar xf data.tar.xz
elif [ -f data.tar.zst ]; then
  tar --zstd -xf data.tar.zst
else
  echo "ERROR: unexpected data.tar compression in upstream DEB" >&2
  exit 1
fi

%build

%install

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/* %{buildroot}%{_datadir}/

install -d -m 0755 %{buildroot}/opt
cp -a opt/localsend_app %{buildroot}/opt/

install -d -m 0755 %{buildroot}%{_bindir}
cat <<-'EOF' > %{buildroot}%{_bindir}/localsend_app
#!/bin/sh
exec /opt/localsend_app/localsend_app "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/localsend_app

%files
%{_bindir}/localsend_app
%{_datadir}/applications/localsend_app.desktop
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/*
%dir %{_datadir}/icons/hicolor/*/apps
%{_datadir}/icons/hicolor/*/apps/localsend_app.png
/opt/localsend_app/

%changelog
