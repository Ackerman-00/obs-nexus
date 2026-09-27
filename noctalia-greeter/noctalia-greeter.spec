Name:           noctalia-greeter
Version:        1.6.0
Release:        0
Summary:        Greeter for Noctalia v5
License:        MIT
Group:          System/GUI/Other
URL:            https://github.com/noctalia-dev/noctalia-greeter
Source0:        %{url}/archive/refs/tags/v%{version}/noctalia-greeter-%{version}.tar.gz
BuildRequires:  gcc-c++
BuildRequires:  meson
BuildRequires:  pkgconfig
BuildRequires:  wlroots-devel
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
BuildRequires:  pkgconfig(libinput)
BuildRequires:  pkgconfig(librsvg-2.0)
BuildRequires:  pkgconfig(libwebp)
BuildRequires:  pkgconfig(libxml-2.0)
BuildRequires:  pkgconfig(nlohmann_json)
BuildRequires:  pkgconfig(pango)
BuildRequires:  pkgconfig(pangocairo)
BuildRequires:  pkgconfig(pangoft2)
BuildRequires:  pkgconfig(stb)
BuildRequires:  pkgconfig(tomlplusplus)
BuildRequires:  pkgconfig(wayland-client)
BuildRequires:  pkgconfig(wayland-egl)
BuildRequires:  pkgconfig(wayland-protocols)
BuildRequires:  pkgconfig(wayland-server)
BuildRequires:  pkgconfig(xkbcommon)
Requires:       dbus-1
# Runtime deps
Requires:       greetd
ExclusiveArch:  x86_64 aarch64

%description
Noctalia Greeter is the screen you see before your desktop session starts.
It lets you pick a user, enter your password, choose a Wayland session, and
pick a color scheme - with the same visual language as Noctalia Shell.

It is built for greetd: greetd starts a small Wayland compositor (Cage),
and the greeter runs inside that session. It is a login UI only, not a
desktop shell or compositor.

Pair it with Noctalia Shell v5 if you want wallpaper and palette synced from
the shell settings.

%prep
%autosetup -n noctalia-greeter-%{version}

%build
%meson
%meson_build

%install
%meson_install

%files
%license LICENSE
%doc README.md
%{_bindir}/noctalia-greeter
%{_bindir}/noctalia-greeter-compositor
%{_bindir}/noctalia-greeter-session
%{_bindir}/noctalia-greeter-apply-appearance
%{_bindir}/noctalia-greeter-print-greetd-config
%{_datadir}/noctalia-greeter
%{_datadir}/polkit-1/actions/org.noctalia.greeter.apply-appearance.policy
%dir %{_prefix}/lib/tmpfiles.d
%{_prefix}/lib/tmpfiles.d/noctalia-greeter.conf

%changelog
