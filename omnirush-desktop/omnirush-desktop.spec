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
# a11y bus daemon: Electron's AT-SPI path needs it at runtime (matches the
# proven fluxer/obsidian Requires set)
Requires:       at-spi2-core
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
Requires:       libnotify.so.4()(64bit)
Requires:       libnspr4.so()(64bit)
Requires:       libnss3.so()(64bit)
Requires:       libnssutil3.so()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
# dlopen-only at runtime (not DT_NEEDED, invisible to auto-deps): libpulse
# for audio playback, libpipewire for capture, libsecret for OS-keyring
# credential storage - proven by strings in the shipped omnirush main
# binary (2/1/2 hits; same Chromium code path as fluxer/obsidian).
# libnotify above is the same strings-proven dlopen (1 hit) and mirrors the
# upstream .deb's libnotify4. libsmime3 IS DT_NEEDED (was missing here).
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
OmniRush.ai desktop shell re-packs the upstream .deb payload under /opt.

%prep
%setup -q -c -T
ar x %{SOURCE0}
# guard every common data.tar compression (upstream could switch at any
# release; the v3.8.0 asset ships data.tar.xz)
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
# plain symlink, NOT update-alternatives: omnirush is the only provider of
# this command (no alternative exists), and the %post --install dance tripped
# rpmlint E: alternative-link-missing / alternative-generic-name-missing /
# update-alternatives-requirement-missing, aborting the TW build at Badness
# 2526 (run 40468416902). Same pattern as hyperframes/fluxer.
ln -sf /opt/omnirush/omnirush %{buildroot}%{_bindir}/omnirush

%files
/opt/omnirush/
%{_bindir}/omnirush
%{_datadir}/applications/*
# upstream ships usr/share/doc/omnirush.ai/changelog.gz; without this entry
# rpmbuild's unpackaged-files check fails the build
%{_datadir}/doc/omnirush.ai/
# own the icon dirs explicitly: hicolor-icon-theme does not own the
# size/apps subdirs on OBS, and unowned dirs fail 50-check-filelist
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
if command -v update-mime-database >/dev/null 2>&1; then update-mime-database /usr/share/mime >/dev/null 2>&1 || true; fi
if command -v update-desktop-database >/dev/null 2>&1; then update-desktop-database /usr/share/applications >/dev/null 2>&1 || true; fi
if command -v apparmor_status >/dev/null 2>&1 && apparmor_status --enabled >/dev/null 2>&1; then
  if [ -f /opt/omnirush/resources/apparmor-profile ]; then
    cp -f /opt/omnirush/resources/apparmor-profile /etc/apparmor.d/omnirush
  fi
fi

%postun
# %postun intentionally minimal: /usr/bin/omnirush is a package-owned
# symlink (removed by rpm itself); the former update-alternatives cleanup
# lived here and is gone with the alternatives misuse fixed.

%changelog
