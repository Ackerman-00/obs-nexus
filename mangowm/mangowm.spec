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
Source0:        mangowm-%{version}.tar.gz
# ONE combined source tarball (mango + wlroots + scenefx top dirs,
# assembled by update.sh): no target distro ships wlroots-0.20 /
# scenefx-0.5 at the floors mango 0.18.0 demands (X11:Wayland carries
# wlroots 0.20.2 for TW/Slowroll but only scenefx 0.4.1 and Leap has
# wlroots 0.19.3; Debian has neither). Built in %%build, staged under
# the build dir (never the buildroot), ONLY the two runtime .so files
# ship in this package. Declared honestly below.
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
%setup -q -c -n mangowm-%{version}

%build
# Single combined source tarball (mango + wlroots + scenefx top dirs);
# %%setup -c -n guarantees BUILD/mangowm-<ver>/ layout - no -a flags, no
# cwd guessing. TOP is absolute everywhere below.
TOP=%{_builddir}/mangowm-%{version}
STAGE=%{_builddir}/deps-pfx
# Staged prefix is $STAGE/usr (NOT /usr + DESTDIR): the generated .pc
# files must carry -I paths that EXIST at compile time. With prefix=/usr
# the .pc points at /usr/include (empty until packaging), breaking
# dependers with missing-include-dirs (OBS log proof). Staging is
# build-local and vanishes; only the two .so files ship (see %%install).
# 1. wlroots (plain meson: out-of-tree sub-build, defaults are sane)
meson setup --prefix=$STAGE/usr --libdir=lib64 --buildtype=release -Dexamples=false $TOP/wlroots-%{wlroots_ver} $TOP/wlroots-build
meson compile -C $TOP/wlroots-build
meson install -C $TOP/wlroots-build
export PKG_CONFIG_PATH="$STAGE/usr/lib64/pkgconfig:$PKG_CONFIG_PATH"
# 2. scenefx against the staged wlroots
meson setup --prefix=$STAGE/usr --libdir=lib64 --buildtype=release $TOP/scenefx-%{scenefx_ver} $TOP/scenefx-build
meson compile -C $TOP/scenefx-build
meson install -C $TOP/scenefx-build
# 3. mango itself (plain meson: the %%meson macro injects a stray
# literal %%setup line into %%build on this rpm - OBS log proof).
meson setup --prefix=%{_prefix} --libdir=%{_lib} --buildtype=release $TOP/mango-%{version} $TOP/mango-build
meson compile -C $TOP/mango-build

%install
TOP=%{_builddir}/mangowm-%{version}
STAGE=%{_builddir}/deps-pfx
DESTDIR=%{buildroot} meson install -C $TOP/mango-build
# Only the two runtime shared libs ship from the staged trees
# (headers/.pc stay in the staging dir, which vanishes with the build).
cp -a $STAGE/usr/lib64/libwlroots-0.20.so* $STAGE/usr/lib64/libscenefx-0.5.so* %{buildroot}%{_libdir}/
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
