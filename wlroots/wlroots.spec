%global wl_ver 0.20.2
Name:           wlroots
Version:        %{wl_ver}
Release:        0
Summary:        Modular Wayland compositor library (0.20 series)
License:        MIT
Group:          Development/Libraries/Other
URL:            https://gitlab.freedesktop.org/wlroots/wlroots
Source0:        wlroots-%{version}.tar.gz
BuildRequires:  fdupes
BuildRequires:  gcc-c++
BuildRequires:  meson >= 1.0.0
BuildRequires:  ninja
BuildRequires:  pkgconfig
BuildRequires:  wayland-protocols-devel
BuildRequires:  pkgconfig(gbm)
BuildRequires:  pkgconfig(glesv2)
BuildRequires:  pkgconfig(egl)
BuildRequires:  pkgconfig(libdisplay-info)
BuildRequires:  pkgconfig(libdrm)
BuildRequires:  pkgconfig(libinput) >= 1.27.1
BuildRequires:  pkgconfig(libliftoff)
BuildRequires:  pkgconfig(libseat)
BuildRequires:  pkgconfig(libudev)
BuildRequires:  pkgconfig(pixman-1)
BuildRequires:  pkgconfig(wayland-client)
BuildRequires:  pkgconfig(wayland-server) >= 1.23.1
BuildRequires:  pkgconfig(xcb)
BuildRequires:  pkgconfig(xcb-composite)
BuildRequires:  pkgconfig(xcb-errors)
BuildRequires:  pkgconfig(xcb-render)
BuildRequires:  pkgconfig(xcb-shm)
BuildRequires:  pkgconfig(xcb-xfixes)
BuildRequires:  pkgconfig(xkbcommon)
ExclusiveArch:  x86_64

%description
wlroots is a modular Wayland compositor library. This package tracks
the 0.20 series required by current compositors (e.g. mangowm,
scenefx 0.5). Companion to the system wlroots on Leap where the
distro ships an older series.

%prep
%autosetup -n wlroots-%{version}

%build
%meson -Dexamples=false
%meson_build

%install
%meson_install
%fdupes %{buildroot}%{_prefix}

%files
%license LICENSE
%doc README.md CONTRIBUTING.md
%{_libdir}/libwlroots-0.20.so*
%{_libdir}/pkgconfig/wlroots-0.20.pc
%{_includedir}/wlr/

%changelog
