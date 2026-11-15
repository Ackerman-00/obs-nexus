%global commit          a50a75d4d74c3355e7398f35097da47b05df572f
%global shortcommit     a50a75d
%global gitdate         20261031223600
%global base_version    2026.10.31.1
%global v8_archive      librusty_v8_release_x86_64-unknown-linux-gnu.a.gz
# sha256: a6476cb94e9b0247081c465424eb793d77732b8db80848132d78cbb50f34b75d
Name:           mixtapes
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        A cross-platform GTK4/Libadwaita YouTube Music client written in Rust
License:        GPL-3.0-or-later
Group:          Productivity/Multimedia/Sound/Other
URL:            https://github.com/m-obeid/Mixtapes
Source0:        mixtapes-%{shortcommit}.tar.gz
Source1:        mixtapes-rpmlintrc
ExclusiveArch:  x86_64

BuildRequires:  cargo
BuildRequires:  cargo-packaging
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  make
BuildRequires:  cmake
BuildRequires:  pkgconf-pkg-config
BuildRequires:  pkgconfig(glib-2.0) >= 2.56
BuildRequires:  pkgconfig(gio-2.0)
BuildRequires:  pkgconfig(gobject-2.0)
BuildRequires:  pkgconfig(gtk4) >= 4.18
BuildRequires:  pkgconfig(libadwaita-1) >= 1.8
BuildRequires:  pkgconfig(webkitgtk-6.0) >= 2.44
BuildRequires:  pkgconfig(javascriptcoregtk-6.0)
BuildRequires:  pkgconfig(libsoup-3.0)
BuildRequires:  pkgconfig(gstreamer-1.0) >= 1.24
BuildRequires:  pkgconfig(gstreamer-base-1.0)
BuildRequires:  pkgconfig(gstreamer-video-1.0)
BuildRequires:  pkgconfig(gstreamer-audio-1.0)
BuildRequires:  pkgconfig(gstreamer-pbutils-1.0)
BuildRequires:  pkgconfig(gstreamer-app-1.0)
BuildRequires:  pkgconfig(gstreamer-play-1.0)
BuildRequires:  pkgconfig(gstreamer-plugins-base-1.0)
BuildRequires:  pkgconfig(gdk-pixbuf-2.0)
BuildRequires:  pkgconfig(pango)
BuildRequires:  pkgconfig(graphene-gobject-1.0)
BuildRequires:  libopenssl-devel
BuildRequires:  pkgconfig(sqlite3) >= 3.34.1
BuildRequires:  desktop-file-utils

Requires:       hicolor-icon-theme
Requires:       gstreamer-plugins-base
Requires:       gstreamer-plugins-good
Requires:       gstreamer-plugins-bad
Requires:       gstreamer-plugins-libav
Requires:       yt-dlp
Requires:       nodejs-default
Recommends:     ffmpeg
Recommends:     xdg-desktop-portal
Recommends:     xdg-desktop-portal-gtk

%description
Mixtapes is a cross-platform desktop application for streaming YouTube Music,
built with GTK4, Libadwaita and GStreamer. The codebase was rewritten from
Python to Rust in October 2026 ("Rustification of Mixtapes").

Compiled specifically for the Nexus repository via automated Git snapshot.

%prep
%autosetup -n Mixtapes-%{commit}

%build
export CARGO_NET_OFFLINE=true
export RUSTY_V8_ARCHIVE=%{_builddir}/Mixtapes-%{commit}/%{v8_archive}
%{cargo_build}

%install
export CARGO_NET_OFFLINE=true
export RUSTY_V8_ARCHIVE=%{_builddir}/Mixtapes-%{commit}/%{v8_archive}
%{cargo_install}
ln -s mixtapes %{buildroot}%{_bindir}/muse

desktop-file-install --dir %{buildroot}%{_datadir}/applications \
    com.pocoguy.Muse.desktop

mkdir -p %{buildroot}%{_datadir}/metainfo
install -Dm644 com.pocoguy.Muse.metainfo.xml \
    %{buildroot}%{_datadir}/metainfo/com.pocoguy.Muse.metainfo.xml

install -Dm644 assets/icons/hicolor/scalable/apps/com.pocoguy.Muse.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/com.pocoguy.Muse.svg
install -Dm644 assets/icons/hicolor/symbolic/apps/com.pocoguy.Muse-symbolic.svg \
    %{buildroot}%{_datadir}/icons/hicolor/symbolic/apps/com.pocoguy.Muse-symbolic.svg

find %{buildroot} \( -path '*/resources/app-update.yml' -o -path '*/resources/package-type' \) -delete 2>/dev/null || true

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/com.pocoguy.Muse.desktop

%files
%license LICENSE
%doc README.md
%{_bindir}/mixtapes
%{_bindir}/muse
%{_datadir}/applications/com.pocoguy.Muse.desktop
%{_datadir}/metainfo/com.pocoguy.Muse.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/com.pocoguy.Muse.svg
%{_datadir}/icons/hicolor/symbolic/apps/com.pocoguy.Muse-symbolic.svg

%changelog
