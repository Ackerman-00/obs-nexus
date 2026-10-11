Name:           wlroots
Version:        0.20.2
Release:        0
Summary:        Modular Wayland compositor library (0.20 series)
License:        MIT
Group:          Development/Libraries/Other
URL:            https://gitlab.freedesktop.org/wlroots/wlroots
Source0:        wlroots-%{version}.tar.gz
# Vendored floors for Leap 16.0 ONLY (owner directive #15 FIX-IT 2026-10-11):
# Leap's baseline (protocols 1.45, libdrm 2.4.124, pixman 0.43.4) sits below
# upstream's unconditional meson floors. Everywhere else the system deps
# satisfy the floors (conditionals off). Pinned in update.sh (WP_VER etc.),
# fetched like Source0 (gitignored, ride the OBS sync).
%if 0%{?suse_version} == 1600
Source10:       wayland-protocols-1.49.tar.xz
Source11:       libdrm-2.4.134.tar.xz
Source12:       pixman-0.46.4.tar.gz
%endif
BuildRequires:  fdupes
BuildRequires:  gcc-c++
BuildRequires:  glslang-devel
BuildRequires:  meson >= 1.3.0
BuildRequires:  ninja
BuildRequires:  pkgconfig
%if 0%{?suse_version} == 1600
# Leap baseline below upstream floors: system devel packages satisfy the
# NAMES here; the vendored .pc files staged in %build satisfy the VERSIONS
# (PKG_CONFIG_PATH order: vendor first). Runtime safety proven by nm audit:
# every linked libdrm/pixman symbol exists in Leap's system libs, and
# protocols XMLs are data-only.
BuildRequires:  wayland-protocols-devel
%else
BuildRequires:  wayland-protocols-devel >= 1.47
%endif
BuildRequires:  pkgconfig(egl)
BuildRequires:  pkgconfig(gbm) >= 21.1
BuildRequires:  pkgconfig(glesv2)
BuildRequires:  pkgconfig(hwdata)
BuildRequires:  pkgconfig(lcms2)
BuildRequires:  pkgconfig(libdisplay-info) >= 0.2.0
%if 0%{?suse_version} == 1600
BuildRequires:  pkgconfig(libdrm)
%else
BuildRequires:  pkgconfig(libdrm) >= 2.4.129
%endif
BuildRequires:  pkgconfig(libinput) >= 1.27.1
BuildRequires:  pkgconfig(libliftoff) >= 0.4.0
BuildRequires:  pkgconfig(libseat) >= 0.2.0
BuildRequires:  pkgconfig(libudev)
%if 0%{?suse_version} == 1600
BuildRequires:  pkgconfig(pixman-1)
# vendored libdrm build needs its intel-backend dep (Leap: 0.18.1)
BuildRequires:  pkgconfig(pciaccess)
%else
BuildRequires:  pkgconfig(pixman-1) >= 0.46.0
%endif
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
scenefx 0.5). Companion to the system wlroots on Leap where the
distro ships an older series.

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
%if 0%{?suse_version} == 1600
# Leap-only: staged newer floors for the scenefx cascade (libdrm tree;
# protocols+pixman stay private to this build). See %build.
Provides:       bundled(wayland-protocols) = 1.49
Provides:       bundled(libdrm) = 2.4.134
Provides:       bundled(pixman) = 0.46.4
%endif

%description devel
Headers and pkgconfig files for building against wlroots 0.20.

%prep
%autosetup -n wlroots-%{version}
%if 0%{?suse_version} == 1600
mkdir -p %{_builddir}/vendor
tar -xf %{SOURCE10} -C %{_builddir}/vendor
tar -xf %{SOURCE11} -C %{_builddir}/vendor
tar -xf %{SOURCE12} -C %{_builddir}/vendor
%endif

%build
%if 0%{?suse_version} == 1600
# FIX-IT (owner directive #15): stage newer floors where Leap 16.0 falls
# short. Runtime safety proven by nm audit (every linked libdrm/pixman
# symbol exists in Leap's system libs; protocols are data-only; final
# DT_NEEDED sonames resolve to system .so files - no rpath added).
VENDOR=%{_builddir}/vendor
PRIVATE=%{_builddir}/vendor-private
VDIR=%{_libdir}/wlroots-vendor
# (a) wayland-protocols 1.49 XMLs, data-only: copied straight into the
# private stage with a hand-written .pc (NO meson/scan step). Rationale
# (OBS log proof, attempt 5): protocols' own meson regenerates enum
# headers with the SYSTEM scanner 1.24 --strict, whose built-in DTD
# rejects the 1.49 color-management XML - while wlroots' own generation
# calls the scanner WITHOUT --strict (protocol/meson.build: plain
# private-code/server-header/client-header), which parses the same XMLs
# fine. Only pkgdatadir + Version are ever read from this .pc.
mkdir -p $PRIVATE/wp/share/wayland-protocols $PRIVATE/wp/share/pkgconfig
cp -a $VENDOR/wayland-protocols-1.49/stable $VENDOR/wayland-protocols-1.49/staging $VENDOR/wayland-protocols-1.49/unstable $PRIVATE/wp/share/wayland-protocols/
printf '%s\n' "prefix=$PRIVATE/wp" "pkgdatadir=$VENDOR/wayland-protocols-1.49" 'Name: wayland-protocols' 'Description: Wayland protocol files (vendored XMLs for Leap baseline)' 'Version: 1.49' > $PRIVATE/wp/share/pkgconfig/wayland-protocols.pc
# (c) pixman 0.46.4 to private stage (own demos/tests off - build input only)
meson setup --prefix=$PRIVATE/px -Dgtk=disabled -Ddemos=disabled -Dtests=disabled $VENDOR/pixman-0.46.4 $VENDOR/build-pix
meson compile -C $VENDOR/build-pix
meson install -C $VENDOR/build-pix
# (b) libdrm 2.4.134 to a private stage, then relocate ONLY its tree under
# the shipped vendor dir by rewriting the prefix line of its .pc files
# (same binaries; libdir/includedir stay ${prefix}-relative so they follow
# the new prefix - verified by the grep below). A direct final-prefix
# configure bakes absolute paths that do not exist at wlroots compile time
# (OBS log proof, attempt 2).
meson setup --prefix=$PRIVATE/drm --libdir=%{_lib} -Dtests=false -Dcairo-tests=disabled -Dvalgrind=disabled -Dman-pages=disabled $VENDOR/libdrm-2.4.134 $VENDOR/build-drm
meson compile -C $VENDOR/build-drm
meson install -C $VENDOR/build-drm
mkdir -p %{buildroot}$VDIR
cp -a $PRIVATE/drm/. %{buildroot}$VDIR/
sed -i "s|^prefix=.*|prefix=$VDIR|" %{buildroot}$VDIR/%{_lib}/pkgconfig/*.pc
grep -H '^prefix=' %{buildroot}$VDIR/%{_lib}/pkgconfig/*.pc
# NOTE: wlroots' OWN build uses ONLY the private stages below. The shipped
# tree (rewritten final prefix) is for the scenefx cascade, NOT for this
# compile - listing it first makes pkg-config emit -I paths that exist
# only under %{buildroot} (OBS log proof, attempt 3).
export PKG_CONFIG_PATH="$PRIVATE/drm/%{_lib}/pkgconfig:$PRIVATE/wp/share/pkgconfig:$PRIVATE/wp/%{_lib}/pkgconfig:$PRIVATE/px/share/pkgconfig:$PRIVATE/px/%{_lib}/pkgconfig:$PKG_CONFIG_PATH"
%endif
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
%if 0%{?suse_version} == 1600
# Leap-only staged floors for the scenefx cascade (libdrm tree: .pc with
# correct final prefix + headers + link .so; runtime keeps system libs).
%{_libdir}/wlroots-vendor/
%endif

%changelog
