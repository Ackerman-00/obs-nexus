%global scen_ver 0.5
Name:           scenefx
Version:        %{scen_ver}
Release:        0
Summary:        Wayland compositor effects library (for wlroots 0.20)
License:        MIT
Group:          Development/Libraries/Other
URL:            https://github.com/wlrfx/scenefx
Source0:        scenefx-%{version}.tar.gz
BuildRequires:  fdupes
BuildRequires:  gcc-c++
BuildRequires:  meson >= 1.0.0
BuildRequires:  ninja
BuildRequires:  pkgconfig
BuildRequires:  wayland-protocols-devel
BuildRequires:  pkgconfig(glesv2)
BuildRequires:  pkgconfig(libdrm) >= 2.4.129
BuildRequires:  pkgconfig(pixman-1) >= 0.43.0
BuildRequires:  pkgconfig(wayland-server)
BuildRequires:  pkgconfig(wlroots-0.20) >= 0.20.0
BuildRequires:  pkgconfig(xkbcommon) >= 1.8.0
Requires:       Mesa-libEGL1
ExclusiveArch:  x86_64

%description
scenefx is a Wayland compositor effects library (blur, shadows,
animations) for wlroots 0.20, used by compositors such as mangowm.
Built against the wlroots package from this same repository.

%prep
%autosetup -n scenefx-%{version}

%build
%meson -Dexamples=false
%meson_build

%install
%meson_install
%fdupes %{buildroot}%{_prefix}

%files
%license LICENSE
%{_libdir}/libscenefx-0.5.so*
%{_libdir}/pkgconfig/scenefx-0.5.pc
%{_includedir}/scenefx/

%changelog
