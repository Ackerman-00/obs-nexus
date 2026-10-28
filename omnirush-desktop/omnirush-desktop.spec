%global debug_package %{nil}
%global __requires_exclude_from ^/opt/omnirush/.*$
%global __provides_exclude_from ^/opt/omnirush/.*$
Name:           omnirush-desktop
Version:        3.8.1
# sha256:  5f8c094be0f7dd7363a83a0b7479822ee36bf98b5b8e642fced58e42b9c52dc2
Release:        0
Summary:        OmniRush.ai desktop shell (Electron)
License:        SUSE-Freeware
Group:          Productivity/Networking/Talk/Clients
URL:            https://omnirush.ai
Source0:        https://github.com/omnirush-ai/omnirush-gui/releases/download/v3.8.1/omnirush-linux-amd64-3.8.1.deb
Source1:        omnirush-desktop-rpmlintrc
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
OmniRush.ai desktop shell re-packs the upstream .deb payload under /opt.

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
install -d %{buildroot}/opt %{buildroot}%{_datadir} %{buildroot}%{_bindir}
if [ -d opt/omnirush ]; then cp -a opt/omnirush %{buildroot}/opt/; fi
if [ -d usr/share ]; then cp -a usr/share/* %{buildroot}%{_datadir}/; fi
if [ -d usr/share/applications ]; then install -d %{buildroot}%{_datadir}/applications; fi
ln -sf /opt/omnirush/omnirush %{buildroot}%{_bindir}/omnirush

%files
/opt/omnirush/
%{_bindir}/omnirush
%{_datadir}/applications/*
%{_datadir}/doc/omnirush.ai/
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/*
%dir %{_datadir}/icons/hicolor/*/apps
%{_datadir}/icons/hicolor/*/*/omnirush.png

%post
if ! { [ -L /proc/self/ns/user ] && unshare --user true; }; then
  chmod 4755 /opt/omnirush/chrome-sandbox || true
else
  chmod 0755 /opt/omnirush/chrome-sandbox || true
fi
if command -v update-mime-database >/dev/null 2>&1; then update-mime-database %{_datadir}/mime >/dev/null 2>&1 || true; fi
if command -v update-desktop-database >/dev/null 2>&1; then update-desktop-database %{_datadir}/applications >/dev/null 2>&1 || true; fi
if command -v apparmor_status >/dev/null 2>&1 && apparmor_status --enabled >/dev/null 2>&1; then
  if [ -f /opt/omnirush/resources/apparmor-profile ]; then
    cp -f /opt/omnirush/resources/apparmor-profile %{apparmor_profilesdir}/omnirush
  fi
fi

%postun

%changelog
