%global debug_package %{nil}
%global __requires_exclude_from ^/opt/omnirush/.*$
%global __provides_exclude_from ^/opt/omnirush/.*$
Name:           omnirush-desktop
Version:        3.8.0
# sha256:  0485c717ac33b29bb7598039f3e2f9455c7fb86163dc3ed11b2053083ee150f4
Release:        0
Summary:        OmniRush.ai desktop shell (Electron)
License:        SUSE-Freeware
Group:          Productivity/Networking/Talk/Clients
URL:            https://omnirush.ai
# Use the upstream DEB as our raw source payload
Source0:        https://github.com/omnirush-ai/omnirush-gui/releases/download/v3.8.0/omnirush-linux-amd64-3.8.0.deb
Source1:        omnirush-desktop-rpmlintrc
BuildRequires:  binutils
BuildRequires:  tar
BuildRequires:  zstd
BuildRequires:  desktop-file-utils
# Hand-mapped soname Depends (Electron runtime, same as fluxer)
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
Requires:       libnspr4.so()(64bit)
Requires:       libnss3.so()(64bit)
Requires:       libnssutil3.so()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
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
OmniRush.ai desktop shell re-packs the upstream .deb payload under /opt.

%prep
%setup -q -c -T
ar x %{SOURCE0}
if [ -f data.tar.xz ]; then tar xf data.tar.xz
elif [ -f data.tar.zst ]; then tar --zstd -xf data.tar.zst
else echo "ERROR: unexpected data.tar compression" >&2; exit 1; fi

%build
:

%install
install -d %{buildroot}/opt %{buildroot}%{_datadir}
if [ -d opt/omnirush ]; then cp -a opt/omnirush %{buildroot}/opt/; fi
if [ -d usr/share ]; then cp -a usr/share/* %{buildroot}%{_datadir}/; fi
if [ -d usr/share/applications ]; then install -d %{buildroot}%{_datadir}/applications; fi

%files
/opt/omnirush/
%{_datadir}/applications/*
%{_datadir}/icons/hicolor/*/*/omnirush.png

%post
if command -v update-alternatives >/dev/null 2>&1; then
  update-alternatives --install /usr/bin/omnirush omnirush /opt/omnirush/omnirush 100 >/dev/null 2>&1 || ln -sf /opt/omnirush/omnirush /usr/bin/omnirush
else
  ln -sf /opt/omnirush/omnirush /usr/bin/omnirush
fi
if ! { [ -L /proc/self/ns/user ] && unshare --user true; }; then
  chmod 4755 /opt/omnirush/chrome-sandbox || true
else
  chmod 0755 /opt/omnirush/chrome-sandbox || true
fi
if command -v update-mime-database >/dev/null 2>&1; then update-mime-database /usr/share/mime >/dev/null 2>&1 || true; fi
if command -v update-desktop-database >/dev/null 2>&1; then update-desktop-database /usr/share/applications >/dev/null 2>&1 || true; fi
if command -v apparmor_status >/dev/null 2>&1 && apparmor_status --enabled >/dev/null 2>&1; then
  if [ -f /opt/omnirush/resources/apparmor-profile ]; then
    cp -f /opt/omnirush/resources/apparmor-profile /etc/apparmor.d/omnirush
  fi
fi

%postun
rm -f /usr/bin/omnirush
if command -v update-alternatives >/dev/null 2>&1; then update-alternatives --remove omnirush /opt/omnirush/omnirush >/dev/null 2>&1 || true; fi

%changelog
