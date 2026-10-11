%global mango_ver      0.18.0
%global wlroots_ver    0.20.2
%global scenefx_ver    0.5
Name:           mangowm
Version:        0.18.0
Release:        0
Summary:        Practical and powerful Wayland compositor (dwm-like, wlroots-based)
License:        GPL-3.0-or-later
Group:          System/GUI/Other
URL:            https://github.com/mangowm/mango
Source0:        https://github.com/mangowm/mango/archive/refs/tags/%{version}.tar.gz
# Bundled build prerequisites: no target distro ships wlroots-0.20 /
# scenefx-0.5 at the floors mango 0.18.0 demands (X11:Wayland carries
# wlroots 0.20.2 for TW/Slowroll but only scenefx 0.4.1 and Leap has
# wlroots 0.19.3; Debian has neither). Built in %build, staged under
# %{_builddir} (never the buildroot), ONLY the two runtime .so files
# ship in this package. Declared honestly below.
Source1:        https://gitlab.freedesktop.org/wlroots/wlroots/-/archive/%{wlroots_ver}/wlroots-%{wlroots_ver}.tar.gz
Source2:        https://github.com/wlrfx/scenefx/archive/refs/tags/%{scenefx_ver}.tar.gz
BuildRequires:  fdupes
BuildRequires:  gcc-c++
BuildRequires:  meson >= 1.0.0
BuildRequires:  ninja
BuildRequires:  pkgconfig
BuildRequires:  desktop-file-utils
BuildRequires:  systemd-rpm-macros
BuildRequires:  wayland-protocols-devel
# Mango direct deps (meson.build dependency() set, 0.18.0)
BuildRequires:  pkgconfig(libcjson)
BuildRequires:  pkgconfig(libdrm)
BuildRequires:  pkgconfig(libinput) >= 1.27.1
BuildRequires:  pkgconfig(libpcre2-8)
BuildRequires:  pkgconfig(pangocairo)
BuildRequires:  pkgconfig(pixman-1)
BuildRequires:  pkgconfig(wayland-client)
BuildRequires:  pkgconfig(wayland-server) >= 1.23.1
# XWayland support (meson feature `xwayland`, default enabled)
BuildRequires:  pkgconfig(xcb)
BuildRequires:  pkgconfig(xcb-icccm)
BuildRequires:  pkgconfig(xcb-randr)
BuildRequires:  pkgconfig(xkbcommon)
# wlroots 0.20 itself needs these at build time
BuildRequires:  pkgconfig(gbm)
BuildRequires:  pkgconfig(glesv2)
BuildRequires:  pkgconfig(egl)
BuildRequires:  pkgconfig(libdisplay-info)
BuildRequires:  pkgconfig(libliftoff)
BuildRequires:  pkgconfig(libseat)
BuildRequires:  pkgconfig(libudev)
BuildRequires:  pkgconfig(xcb-composite)
BuildRequires:  pkgconfig(xcb-errors)
BuildRequires:  pkgconfig(xcb-render)
BuildRequires:  pkgconfig(xcb-shm)
BuildRequires:  pkgconfig(xcb-xfixes)
Provides:       bundled(wlroots) = %{wlroots_ver}
Provides:       bundled(scenefx) = %{scenefx_ver}
Provides:       wayland-compositor
Requires:       Mesa-dri
Requires:       Mesa-libEGL1
Requires:       hwdata
Requires:       xwayland
ExclusiveArch:  x86_64

%description
Mango is a fast, feature-rich Wayland compositor built on dwl,
wlroots and scenefx - scrollable tiling, animations, blur/shadow
effects, tags, scratchpad and IPC. wlroots %{wlroots_ver} and
scenefx %{scenefx_ver} are built from source inside this package
because no target distro ships them at the required floors.

%prep
%autosetup -n mango-%{version} -a1 -a2

%build
# rpm lands %build inside BUILD/mangowm-<ver>-build/mango-<ver> (multi-source
# %autosetup layout, proven in OBS logs) - or directly in mango-<ver>.
# Either way the next line ends in the mango tree; sibling trees (wlroots,
# scenefx) and staging live one level up, addressed relatively so no
# assumption about the parent dir name is needed.
cd mango-%{version} 2>/dev/null || true
STAGE=$PWD/../deps-pfx
# 1. wlroots (plain meson: out-of-tree sub-build, defaults are sane)
meson setup --prefix=%{_prefix} --libdir=%{_lib} --buildtype=release -Dexamples=false ../wlroots-%{wlroots_ver} ../wlroots-build
meson compile -C ../wlroots-build
DESTDIR=$STAGE meson install -C ../wlroots-build
export PKG_CONFIG_PATH="$STAGE%{_libdir}/pkgconfig:$PKG_CONFIG_PATH"
# 2. scenefx against the staged wlroots
meson setup --prefix=%{_prefix} --libdir=%{_lib} --buildtype=release ../scenefx-%{scenefx_ver} ../scenefx-build
meson compile -C ../scenefx-build
DESTDIR=$STAGE meson install -C ../scenefx-build
export PKG_CONFIG_PATH="$STAGE%{_libdir}/pkgconfig:$PKG_CONFIG_PATH"
# 3. mango itself (house macros, proven by protonplus)
%meson
%meson_build

%install
cd mango-%{version} 2>/dev/null || true
STAGE=$PWD/../deps-pfx
%meson_install
# Only the two runtime shared libs ship from the staged trees
# (headers/.pc stay in the staging dir, which vanishes with the build).
cp -a $STAGE%{_libdir}/libwlroots-0.20.so* $STAGE%{_libdir}/libscenefx-0.5.so* %{buildroot}%{_libdir}/
%fdupes %{buildroot}%{_prefix}

%check
desktop-file-validate %{buildroot}%{_datadir}/wayland-sessions/mango.desktop || :

%files
%license LICENSE LICENSE.dwl LICENSE.tinywl LICENSE.dwm LICENSE.sway
%doc README.md
%{_bindir}/mango
%{_bindir}/mmsg
%{_bindir}/mangonag
%{_mandir}/man1/mmsg.1%{?ext_man}
%{_mandir}/man1/mangonag.1%{?ext_man}
%dir %{_datadir}/wayland-sessions
%{_datadir}/wayland-sessions/mango.desktop
%dir %{_datadir}/xdg-desktop-portal
%{_datadir}/xdg-desktop-portal/mango-portals.conf
%dir %{_sysconfdir}/mango
%config(noreplace) %{_sysconfdir}/mango/config.conf
%config(noreplace) %{_sysconfdir}/mango/config.toml
%{_userunitdir}/mango-session.target
%{_libdir}/libwlroots-0.20.so*
%{_libdir}/libscenefx-0.5.so*

%changelog
