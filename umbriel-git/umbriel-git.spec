%global commit          a909081a934a80bb7685080884ffaaa30c857e4c
%global shortcommit     a909081
%global gitdate         20261123014939
%global base_version    0.1.0
Name:           umbriel-git
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        Wayland compositor with scrolling and dwindle layouts
License:        MIT
Group:          System/GUI/Other
URL:            https://github.com/noctalia-dev/umbriel
Source0:        umbriel-%{shortcommit}.tar.gz
Source1:        umbriel-git-rpmlintrc
ExclusiveArch:  x86_64

BuildRequires:  meson >= 1.3
BuildRequires:  gcc-c++
BuildRequires:  git
BuildRequires:  ninja
BuildRequires:  systemd-rpm-macros
BuildRequires:  pkgconfig(wlroots-0.20) >= 0.20.1
BuildRequires:  pkgconfig(wayland-server) >= 1.24
BuildRequires:  pkgconfig(wayland-client)
BuildRequires:  pkgconfig(wayland-protocols) >= 1.47
BuildRequires:  pkgconfig(xkbcommon) >= 1.10.0
BuildRequires:  pkgconfig(libinput) >= 1.29
BuildRequires:  pkgconfig(libeis-1.0) >= 1.3
BuildRequires:  pkgconfig(libudev)
BuildRequires:  pkgconfig(libsystemd) >= 243
BuildRequires:  pkgconfig(pixman-1) >= 0.43
BuildRequires:  pkgconfig(libdrm) >= 2.4.129
BuildRequires:  pkgconfig(libdisplay-info) >= 0.3.0
BuildRequires:  pkgconfig(cairo)
BuildRequires:  pkgconfig(pangocairo)
BuildRequires:  pkgconfig(tomlplusplus)
BuildRequires:  pkgconfig(nlohmann_json)
BuildRequires:  pkgconfig(xcb)
BuildRequires:  pkgconfig(xcb-icccm)
BuildRequires:  pkgconfig(xcb-ewmh)
BuildRequires:  pkgconfig(xcb-shape)
BuildRequires:  pkgconfig(xcb-randr)
BuildRequires:  pkgconfig(xcb-render)
BuildRequires:  pkgconfig(xcb-xfixes)
BuildRequires:  pkgconfig(xcb-xtest)
BuildRequires:  pkgconfig(egl)
BuildRequires:  pkgconfig(glesv2)
BuildRequires:  pkgconfig(gbm)
BuildRequires:  pkgconfig(lcms2)
BuildRequires:  pkgconfig(jemalloc)

Requires:       xdg-desktop-portal-umbriel-git
Requires:       xdg-desktop-portal-gnome
Requires:       x11-tools
Recommends:     xwayland
Recommends:     noctalia
Recommends:     (kitty or alacritty or foot)
Recommends:     (nautilus or nemo)

Conflicts:      umbriel
Provides:       wayland-compositor

%description
Umbriel is a Wayland compositor designed for daily use, with scrolling and
dwindle layouts, per-output workspaces, window rules, blur, shadows, and
fluid animations. Built in C++23 on wlroots and the Noctalia SceneFX fork,
with Xwayland and portal screen capture and sharing by
xdg-desktop-portal-umbriel.

Compiled specifically for the Nexus repository via automated Git snapshot.

%prep
%autosetup -n umbriel-%{commit}

%build
%meson -Db_lto=true -Dtests=disabled -Dharness=disabled -Dlocaled=enabled -Dtracy=disabled
%meson_build

%install
%meson_install

find %{buildroot} \( -path '*/resources/app-update.yml' -o -path '*/resources/package-type' \) -delete 2>/dev/null || true
%post
%systemd_user_post umbriel.service

%preun
%systemd_user_preun umbriel.service

%postun
%systemd_user_postun umbriel.service

%files
%license LICENSE
%doc README.md
%{_bindir}/umbriel
%{_bindir}/start-umbriel
%dir %{_datadir}/umbriel
%config(noreplace) %{_datadir}/umbriel/config.toml
%{_datadir}/umbriel/effects/
%dir %{_datadir}/wayland-sessions
%{_datadir}/wayland-sessions/umbriel.desktop
%{_userunitdir}/umbriel.service
%{_userunitdir}/umbriel-session.target
%{_userunitdir}/umbriel-shutdown.target

%changelog
