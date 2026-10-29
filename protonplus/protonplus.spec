%define         appid com.vysp3r.ProtonPlus
Name:           protonplus
Version:        0.6.8
Release:        0
ExclusiveArch:  x86_64
Summary:        A Wine and Proton-based compatibility tools manager for GNOME
License:        GPL-3.0-only
Group:          System/GUI/Other
URL:            https://github.com/vysp3r/ProtonPlus
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz
BuildRequires:  desktop-file-utils
BuildRequires:  fdupes
BuildRequires:  gettext-runtime
BuildRequires:  meson >= 1.0.0
BuildRequires:  ninja
BuildRequires:  pkgconf
BuildRequires:  pkgconfig
BuildRequires:  python3
BuildRequires:  vala
BuildRequires:  pkgconfig(appstream)
BuildRequires:  pkgconfig(cairo)
BuildRequires:  pkgconfig(gee-0.8)
BuildRequires:  pkgconfig(gio-unix-2.0)
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  pkgconfig(gtk4)
BuildRequires:  pkgconfig(json-glib-1.0)
BuildRequires:  pkgconfig(libadwaita-1) >= 1.6.0
BuildRequires:  pkgconfig(libarchive)
BuildRequires:  pkgconfig(libnotify)
BuildRequires:  pkgconfig(libsoup-3.0)
BuildRequires:  pkgconfig(sdl3) >= 3.2.0
Requires:       hicolor-icon-theme
Requires:       libGLESv2.so.2()(64bit)
Conflicts:      ProtonPlus

%description
ProtonPlus is a Proton version manager for installing and managing Proton
versions. It works with Steam, Lutris, Heroic Games Launcher and Bottles. It
uses GTK4.

%package lang
Summary:        Translations for package %{name}
Group:          System/Localization
Requires:       %{name} = %{version}-%{release}
BuildArch:      noarch

%description lang
Provides translations for the "%{name}" package.

%prep
%autosetup -n ProtonPlus-%{version}

%build
%meson --prefix=%{_prefix}
%meson_build

%install
%meson_install
%find_lang %{appid}
%fdupes %{buildroot}

%check
%meson_test

%files
%{_bindir}/protonplus
%{_datadir}/metainfo/%{appid}.metainfo.xml
%{_datadir}/applications/%{appid}.desktop
%{_datadir}/glib-2.0/schemas/%{appid}.gschema.xml
%{_datadir}/icons/hicolor/*/apps/%{appid}.png

%files lang -f %{appid}.lang

%changelog
