Name:           scenefx
Version:        0.5
Release:        0
Summary:        Wayland compositor effects library (for wlroots 0.20)
License:        MIT
Group:          Development/Libraries/Other
URL:            https://github.com/wlrfx/scenefx
Source0:        scenefx-%{version}.tar.gz
BuildRequires:  fdupes
BuildRequires:  gcc-c++
BuildRequires:  meson >= 1.3.0
BuildRequires:  ninja
BuildRequires:  pkgconfig
BuildRequires:  wayland-protocols-devel >= 1.41
BuildRequires:  pkgconfig(egl)
BuildRequires:  pkgconfig(gbm)
BuildRequires:  pkgconfig(glesv2)
BuildRequires:  pkgconfig(lcms2)
%if 0%{?suse_version} == 1600
# Leap: system libdrm-devel (2.4.124) below the >= 2.4.129 floor; the
# vendored .pc inside wlroots-devel (shipped by this repo's wlroots Leap
# build, PKG_CONFIG_PATH below) satisfies the version. Runtime safety:
# every linked libdrm symbol exists in Leap's system libdrm (nm audit).
BuildRequires:  pkgconfig(libdrm)
%else
BuildRequires:  pkgconfig(libdrm) >= 2.4.129
%endif
BuildRequires:  pkgconfig(pixman-1) >= 0.43.0
BuildRequires:  pkgconfig(wayland-server) >= 1.24.0
BuildRequires:  pkgconfig(wlroots-0.20) >= 0.20.0
BuildRequires:  pkgconfig(xkbcommon) >= 1.8.0
ExclusiveArch:  x86_64

%description
scenefx is a Wayland compositor effects library (blur, shadows,
animations) for wlroots 0.20, used by compositors such as mangowm.
Built against the wlroots package from this same repository.

%package -n libscenefx-0_5
Summary:        Wayland compositor effects library (for wlroots 0.20)
Group:          System/Libraries
Requires:       Mesa-libEGL1

%description -n libscenefx-0_5
scenefx shared objects (effects library for wlroots 0.20 compositors
such as mangowm).

%package devel
Summary:        Development files for scenefx 0.5
Group:          Development/Libraries/Other
Requires:       libscenefx-0_5 = %{version}

%description devel
Headers and pkgconfig files for building against scenefx 0.5.

%prep
%autosetup -n scenefx-%{version}

%build
%if 0%{?suse_version} == 1600
# Leap cascade: resolve libdrm>=2.4.129 from the vendor tree shipped in
# this repo's wlroots-devel (built by the FIX-IT recipe above). All other
# floors are satisfied by the Leap baseline itself.
export PKG_CONFIG_PATH="%{_libdir}/wlroots-vendor/%{_lib}/pkgconfig:%{_libdir}/wlroots-vendor/share/pkgconfig:$PKG_CONFIG_PATH"
%endif
%meson -Dexamples=false
%meson_build

%install
%meson_install
%fdupes %{buildroot}%{_prefix}

%post -n libscenefx-0_5 -p /sbin/ldconfig
%postun -n libscenefx-0_5 -p /sbin/ldconfig

%files
%license LICENSE

%files -n libscenefx-0_5
%{_libdir}/libscenefx-0.5.so*

%files devel
%{_includedir}/scenefx-0.5/
%{_libdir}/pkgconfig/scenefx-0.5.pc

%changelog
