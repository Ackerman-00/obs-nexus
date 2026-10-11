Name:           wlroots
Version:        0.20.2
Release:        0
Summary:        Modular Wayland compositor library (0.20 series)
License:        MIT
Group:          Development/Libraries/Other
URL:            https://gitlab.freedesktop.org/wlroots/wlroots
Source0:        wlroots-%{version}.tar.gz
BuildRequires:  fdupes
BuildRequires:  gcc-c++
BuildRequires:  glslang-devel
BuildRequires:  meson >= 1.3.0
BuildRequires:  ninja
BuildRequires:  pkgconfig
BuildRequires:  wayland-protocols-devel >= 1.47
BuildRequires:  pkgconfig(egl)
BuildRequires:  pkgconfig(gbm) >= 21.1
BuildRequires:  pkgconfig(glesv2)
BuildRequires:  pkgconfig(hwdata)
BuildRequires:  pkgconfig(lcms2)
BuildRequires:  pkgconfig(libdisplay-info) >= 0.2.0
BuildRequires:  pkgconfig(libdrm) >= 2.4.129
BuildRequires:  pkgconfig(libinput) >= 1.27.1
BuildRequires:  pkgconfig(libliftoff) >= 0.4.0
BuildRequires:  pkgconfig(libseat) >= 0.2.0
BuildRequires:  pkgconfig(libudev)
BuildRequires:  pkgconfig(pixman-1) >= 0.46.0
BuildRequires:  pkgconfig(vulkan) >= 1.2.182
BuildRequires:  pkgconfig(wayland-client)
BuildRequires:  pkgconfig(wayland-scanner)
BuildRequires:  pkgconfig(wayland-server) >= 1.24.0
BuildRequires:  pkgconfig(xcb)
BuildRequires:  pkgconfig(xcb-composite)
BuildRequires:  pkgconfig(xcb-dri3)
BuildRequires:  pkgconfig(xcb-errors)
BuildRequires:  pkgconfig(xcb-ewmh)
BuildRequires:  pkgconfig(xcb-icccm)
BuildRequires:  pkgconfig(xcb-present)
BuildRequires:  pkgconfig(xcb-render)
BuildRequires:  pkgconfig(xcb-renderutil)
BuildRequires:  pkgconfig(xcb-res)
BuildRequires:  pkgconfig(xcb-shm)
BuildRequires:  pkgconfig(xcb-xfixes) >= 1.15
BuildRequires:  pkgconfig(xcb-xinput)
BuildRequires:  pkgconfig(xkbcommon) >= 1.8.0
BuildRequires:  pkgconfig(xwayland)
ExclusiveArch:  x86_64

%description
wlroots is a modular Wayland compositor library. This package tracks
the 0.20 series required by current compositors (e.g. mangowm,
scenefx 0.5).

%package -n libwlroots-0_20
Summary:        Modular Wayland compositor library (0.20 series)
Group:          System/Libraries

%description -n libwlroots-0_20
wlroots is a modular Wayland compositor library (0.20 series shared
objects, used by compositors such as mangowm via scenefx).

%package devel
Summary:        Development files for wlroots 0.20
Group:          Development/Libraries/Other
Requires:       libwlroots-0_20 = %{version}

%description devel
Headers and pkgconfig files for building against wlroots 0.20.

%prep
%autosetup -n wlroots-%{version}

%build
%meson -Dexamples=false
%meson_build

%install
%meson_install
%fdupes %{buildroot}%{_prefix}

%post -n libwlroots-0_20 -p /sbin/ldconfig
%postun -n libwlroots-0_20 -p /sbin/ldconfig

%files
%license LICENSE
%doc README.md CONTRIBUTING.md

%files -n libwlroots-0_20
%{_libdir}/libwlroots-0.20.so*

%files devel
%{_includedir}/wlroots-0.20/
%{_libdir}/pkgconfig/wlroots-0.20.pc

%changelog
