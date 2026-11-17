%global commit          ed91d04331b03257d5bd58a075b9cd6743d3efb2
%global shortcommit     ed91d04
%global gitdate         20261117160213
%global base_version    0.1.0
Name:           xdg-desktop-portal-umbriel-git
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        XDG Desktop Portal backend for Umbriel
License:        MIT
Group:          System/Libraries/Other
URL:            https://github.com/noctalia-dev/xdg-desktop-portal-umbriel
Source0:        xdg-desktop-portal-umbriel-%{shortcommit}.tar.gz
Source1:        xdg-desktop-portal-umbriel-git-rpmlintrc
ExclusiveArch:  x86_64

BuildRequires:  meson >= 1.3
BuildRequires:  gcc-c++
BuildRequires:  ninja
BuildRequires:  systemd-rpm-macros
BuildRequires:  pkgconfig(sdbus-c++) >= 2.0.0
BuildRequires:  pkgconfig(libpipewire-0.3)
BuildRequires:  pkgconfig(wayland-client)
BuildRequires:  pkgconfig(wayland-protocols) >= 1.39
BuildRequires:  pkgconfig(wayland-scanner)
BuildRequires:  pkgconfig(libdrm)
BuildRequires:  pkgconfig(gbm)
BuildRequires:  pkgconfig(cairo)
BuildRequires:  pkgconfig(tomlplusplus)
BuildRequires:  pkgconfig(nlohmann_json)
BuildRequires:  pkgconfig(gtk4) >= 4.12
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  pkgconfig(gio-2.0)
BuildRequires:  pkgconfig(libei-1.0) >= 1.3

Requires:       xdg-desktop-portal
Recommends:     slurp
Conflicts:      xdg-desktop-portal-umbriel

%description
An xdg-desktop-portal backend for the Umbriel compositor, providing
Screencast and Screenshot portal interfaces for portal-based screen capture
and sharing, with a GTK4 share picker.
Compiled specifically for the Nexus repository via automated Git snapshot.

%prep
%autosetup -n xdg-desktop-portal-umbriel-%{commit}

%build
%meson -Db_lto=true -Dpicker=enabled
%meson_build

%install
%meson_install

find %{buildroot} \( -path '*/resources/app-update.yml' -o -path '*/resources/package-type' \) -delete 2>/dev/null || true
%check
%meson_test

%files
%license LICENSE
%doc README.md
%{_userunitdir}/xdg-desktop-portal-umbriel.service
%{_libexecdir}/umbriel-share-picker
%{_libexecdir}/xdg-desktop-portal-umbriel
%{_datadir}/dbus-1/services/org.freedesktop.impl.portal.desktop.umbriel.service
%dir %{_datadir}/xdg-desktop-portal
%dir %{_datadir}/xdg-desktop-portal/portals
%{_datadir}/xdg-desktop-portal/portals/umbriel.portal
%config(noreplace) %{_datadir}/xdg-desktop-portal/umbriel-portals.conf

%changelog
