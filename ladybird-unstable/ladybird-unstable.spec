%global debug_package %{nil}
%global __requires_exclude_from ^/opt/ladybird/.*$
%global __provides_exclude_from ^/opt/ladybird/.*$
%global __brp_mangle_shebangs_exclude_from ^/opt/ladybird/.*$
%global commit         ea3dc927bdb30a60a75c5004a88e3547b8c1a270
%global shortcommit     ea3dc92
%global gitdate         20261113173302
%global base_version   0.0.0

Name:           ladybird-unstable
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        Truly independent web browser (git master; unstable)
License:        BSD-2-Clause
Group:          Productivity/Networking/Web/Browsers
URL:            https://ladybird.org
Source0:        ladybird-unstable-%{version}.tar.gz
Source1:        check-bundled-libs.py
ExclusiveArch:  x86_64

BuildRequires:  desktop-file-utils
Requires:       hicolor-icon-theme
Requires:       libcairo.so.2()(64bit)
Requires:       libcups.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libdrm.so.2()(64bit)
Requires:       libexpat.so.1()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libicudata.so.78()(64bit)
Requires:       libicui18n.so.78()(64bit)
Requires:       libicuuc.so.78()(64bit)
Requires:       libncurses.so.6()(64bit)
Requires:       libpulse.so.0()(64bit)
Requires:       libQt6Core.so.6()(64bit)
Requires:       libQt6Gui.so.6()(64bit)
Requires:       libQt6Positioning.so.6()(64bit)
Requires:       libQt6Widgets.so.6()(64bit)
Requires:       libtinfo.so.6()(64bit)
Requires:       libvulkan.so.1()(64bit)
Requires:       libwayland-client.so.0()(64bit)
Requires:       libxcb-icccm.so.4()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires(posttrans): gtk3-tools
Requires(postun): gtk3-tools
Recommends:     mesa-vulkan-drivers
Recommends:     qt6-qtwayland

%description
Ladybird is a truly independent web browser built from the upstream git master
branch. This package is unstable by construction: it tracks upstream main.
The payload is built by the repo's own CI pipeline; OBS repacks it offline.

%prep
%setup -q -n ladybird-unstable-%{version}

%build

%install
install -d %{buildroot}/opt %{buildroot}%{_bindir} %{buildroot}%{_datadir}
cp -a opt/ladybird %{buildroot}/opt/
if [ -d usr/bin ]; then cp -a usr/bin/* %{buildroot}%{_bindir}/; fi
if [ -d usr/share ]; then cp -a usr/share/* %{buildroot}%{_datadir}/; fi
install -Dpm0644 opt/ladybird/share/icons/hicolor/scalable/apps/org.ladybird.Ladybird.svg %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/org.ladybird.Ladybird.svg 2>/dev/null || true
python3 %{SOURCE1} %{buildroot}/opt/ladybird/lib64

%files
%license LICENSE
/opt/ladybird
%{_bindir}/ladybird
%{_datadir}/applications/org.ladybird.Ladybird.desktop
%{_datadir}/dbus-1/services/org.ladybird.Ladybird.service
%{_datadir}/icons/hicolor/scalable/apps/org.ladybird.Ladybird.svg
%{_metainfodir}/org.ladybird.Ladybird.metainfo.xml

%post
gtk-update-icon-cache -q %{_datadir}/icons/hicolor 2>/dev/null || :

%postun
gtk-update-icon-cache -q %{_datadir}/icons/hicolor 2>/dev/null || :

%changelog
