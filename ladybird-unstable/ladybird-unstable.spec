%global _lto_cflags %{nil}
%global __requires_exclude_from ^/opt/ladybird/.*$
%global __provides_exclude_from ^/opt/ladybird/.*$
%global __brp_mangle_shebangs_exclude_from ^/opt/ladybird/.*$
%global commit         3548021fc1a0cc9934331f62649cdad7761cdf09
%global shortcommit    3548021
%global gitdate        20261113125931
%global base_version   0.0.0

Name:           ladybird-unstable
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        Truly independent web browser (git master; unstable)
License:        BSD-2-Clause
Group:          Productivity/Networking/Web/Browsers
URL:            https://ladybird.org
Source0:        https://github.com/LadybirdBrowser/ladybird/archive/%{commit}.tar.gz
# sha256:  2a2cd4b34623306f16ee92d9c575668f8b125c6a2c9afe273f2ddb2404ca9391
Source1:        check-bundled-libs.py
ExclusiveArch:  x86_64

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
Recommends:     mesa-vulkan-drivers
Recommends:     qt6-qtwayland

BuildRequires:  autoconf-archive
BuildRequires:  automake
BuildRequires:  binutils
BuildRequires:  ccache
BuildRequires:  cmake
BuildRequires:  curl
BuildRequires:  desktop-file-utils
BuildRequires:  file
BuildRequires:  findutils
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  git
BuildRequires:  glslang-devel
BuildRequires:  libdrm-devel
BuildRequires:  libglvnd-devel
BuildRequires:  liberation-fonts
BuildRequires:  libpulse-devel
BuildRequires:  libtool
BuildRequires:  lld
BuildRequires:  make
BuildRequires:  nasm
BuildRequires:  ncurses-devel
BuildRequires:  ninja
BuildRequires:  patch
BuildRequires:  patchelf
BuildRequires:  perl
BuildRequires:  pkgconf
BuildRequires:  python3
BuildRequires:  qt6-base-devel
BuildRequires:  qt6-base-private-devel
BuildRequires:  qt6-positioning-devel
BuildRequires:  qt6-tools-devel
BuildRequires:  qt6-wayland-devel
BuildRequires:  rust
BuildRequires:  cargo
BuildRequires:  tar
BuildRequires:  unzip
BuildRequires:  wayland-devel
BuildRequires:  xcb-util-wm-devel
BuildRequires:  xz
BuildRequires:  zip
BuildRequires:  zstd

%description
Ladybird is a truly independent web browser built from the upstream git master
branch. This package is unstable by construction: it tracks upstream main.

%prep
%autosetup -n ladybird-%{commit}

%build
export VCPKG_FORCE_SYSTEM_BINARIES=1
if ! curl -fsS --max-time 20 -o /dev/null https://github.com/ ; then
  echo 'ERROR: no outbound network in this build container - vcpkg downloads its ports' >&2
  exit 1
fi
python3 Meta/ladybird.py vcpkg --preset Release
cmake --preset Release -S . -B Build/release -DBUILD_TESTING=OFF -DENABLE_INSTALL_FREEDESKTOP_FILES=OFF -DCMAKE_INSTALL_PREFIX=/opt/ladybird -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=OFF -DENABLE_CI_BASELINE_CPU=ON
if grep -q -- '-march=native' Build/release/build.ninja; then
  echo 'ERROR: -march=native leaked into the build' >&2
  exit 1
fi
cmake --build Build/release --parallel %{?_smp_mflags}

%install
DESTDIR=%{buildroot} cmake --install Build/release --component ladybird_Runtime
DESTDIR=%{buildroot} cmake --install Build/release --component Lagom_Runtime
DESTDIR=%{buildroot} cmake --install Build/release --component ladybird_SystemIntegration
mkdir -p %{buildroot}/opt/ladybird/lib64
VCPKG_LIBS=$(find Build/release/vcpkg_installed/*-linux-dynamic/lib -maxdepth 1 -name '*.so*' -print)
[ -n "$VCPKG_LIBS" ] || { echo "FATAL: no vcpkg shared libraries found to bundle" >&2; exit 1; }
cp -a $VCPKG_LIBS %{buildroot}/opt/ladybird/lib64/
chmod -R u+w %{buildroot}/opt/ladybird
rm -f %{buildroot}/opt/ladybird/lib64/libicu*.so*
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
