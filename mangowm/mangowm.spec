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
# wlroots + scenefx from the sibling packages in this repository
BuildRequires:  pkgconfig(scenefx-0.5)
BuildRequires:  pkgconfig(wlroots-0.20)
Provides:       wayland-compositor
Requires:       Mesa-dri
Requires:       Mesa-libEGL1
Requires:       hwdata
Requires:       xwayland
ExclusiveArch:  x86_64

%description
Mango is a fast, feature-rich Wayland compositor built on dwl,
wlroots and scenefx - scrollable tiling, animations, blur/shadow
effects, tags, scratchpad and IPC. Links the wlroots and scenefx
packages from this same repository.

%prep
%autosetup -n mango-%{version}

%build
%meson
%meson_build

%install
%meson_install
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

%changelog
