# Raw upstream tag version (GitHub archive dir uses this, no v prefix)
%global tagver 5.2.0
Name:           noctalia
Version:        5.2.0
# Epoch 1: the 2026-09-03 sync wrongly shipped Version 5.01 (update.sh stripped
# the dot: 5.0.1 -> 5.01). rpm vercmp sorts 5.01 NEWER than 5.0.1, so the Epoch
# is required for the corrected version to upgrade cleanly. Never remove it.
Epoch:          1
Release:        0
Summary:        A sleek and minimal desktop shell thoughtfully crafted for Wayland
License:        MIT
Group:          System/GUI/Other
URL:            https://github.com/noctalia-dev/noctalia
Source0:        %{url}/archive/refs/tags/v%{tagver}/%{name}-%{tagver}.tar.gz
BuildRequires:  fdupes
BuildRequires:  gcc-c++
BuildRequires:  hicolor-icon-theme
BuildRequires:  meson
BuildRequires:  pkgconfig
BuildRequires:  pkgconfig(cairo)
BuildRequires:  pkgconfig(cairo-ft)
BuildRequires:  pkgconfig(egl)
BuildRequires:  pkgconfig(epoxy)
BuildRequires:  pkgconfig(fontconfig)
BuildRequires:  pkgconfig(freetype2)
BuildRequires:  pkgconfig(gio-2.0)
BuildRequires:  pkgconfig(glesv2)
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  pkgconfig(gobject-2.0)
BuildRequires:  pkgconfig(harfbuzz)
BuildRequires:  pkgconfig(jemalloc)
BuildRequires:  pkgconfig(libcurl)
BuildRequires:  pkgconfig(libical)
BuildRequires:  pkgconfig(libjxl)
BuildRequires:  pkgconfig(libjxl_threads)
BuildRequires:  pkgconfig(libpipewire-0.3)
BuildRequires:  pkgconfig(libqalculate)
BuildRequires:  pkgconfig(librsvg-2.0)
BuildRequires:  pkgconfig(libsecret-1) >= 0.20
BuildRequires:  pkgconfig(libsodium) >= 1.0.18
BuildRequires:  pkgconfig(libwebp)
BuildRequires:  pkgconfig(libwebpdemux)
BuildRequires:  pkgconfig(libxml-2.0)
BuildRequires:  pkgconfig(md4c)
BuildRequires:  pkgconfig(nlohmann_json)
BuildRequires:  pkgconfig(pam)
BuildRequires:  pkgconfig(pango)
BuildRequires:  pkgconfig(pangocairo)
BuildRequires:  pkgconfig(pangoft2)
BuildRequires:  pkgconfig(polkit-agent-1)
BuildRequires:  pkgconfig(polkit-gobject-1)
BuildRequires:  pkgconfig(sdbus-c++) >= 2.0.0
BuildRequires:  pkgconfig(sndfile)
BuildRequires:  pkgconfig(stb)
BuildRequires:  pkgconfig(tomlplusplus)
BuildRequires:  pkgconfig(wayland-client)
BuildRequires:  pkgconfig(wayland-egl)
BuildRequires:  pkgconfig(wayland-protocols)
BuildRequires:  pkgconfig(wireplumber-0.5)
BuildRequires:  pkgconfig(xkbcommon)
Requires:       qalculate
Recommends:     upower
Conflicts:      noctalia-git

%description
A lightweight Wayland shell and bar built directly on Wayland + OpenGL ES,
with no Qt or GTK dependency.

Noctalia is in early development. Expect breaking configuration and
behavior changes while the project is still taking shape.

%prep
%autosetup -n noctalia-%{tagver}

%build
%meson
%meson_build

%install
%meson_install

find %{buildroot}%{_datadir}/noctalia/assets/templates \
	-type f -name '*.sh' \
	-exec sed -i '1s|^#!%{_bindir}/env bash$|#!%{_bindir}/bash|' {} +

find %{buildroot}%{_datadir}/noctalia/assets/templates \
	-type f -name '*.py' \
	-exec sed -i '1s|^#!%{_bindir}/env python3$|#!%{_bindir}/python3|' {} +

find %{buildroot}%{_datadir}/noctalia/assets/templates \
	-type f \( -name '*.sh' -o -name '*.py' \) \
	-exec chmod 0755 {} +

%fdupes %{buildroot}%{_datadir}

%files
%license LICENSE
%doc README.md
%{_bindir}/noctalia
%{_datadir}/noctalia
%{_datadir}/applications/dev.noctalia.Noctalia.desktop
%{_datadir}/icons/hicolor/scalable/apps/noctalia.svg

%changelog
