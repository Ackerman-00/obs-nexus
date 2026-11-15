%global commit          a50a75d4d74c3355e7398f35097da47b05df572f
%global shortcommit     a50a75d
%global gitdate         20261031223600
%global base_version    0
Name:           mixtapes
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        A cross-platform GTK4/Libadwaita YouTube Music client written in Rust
License:        GPL-3.0-or-later
Group:          Productivity/Multimedia/Sound/Other
URL:            https://github.com/m-obeid/Mixtapes
Source0:        mixtapes-%{shortcommit}.tar.gz
Source1:        mixtapes-rpmlintrc
exclusiveArch:  x86_64

BuildRequires:  cargo
BuildRequires:  rust
BuildRequires:  rust-srpm-macros
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  make
BuildRequires:  cmake
BuildRequires:  pkgconf-pkg-config
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  pkgconfig(gtk4) >= 4.18
BuildRequires:  glib2-devel
BuildRequires:  pkgconfig(libadwaita-1) >= 1.8
BuildRequires:  pkgconfig(webkitgtk-6.0) >= 2.44
BuildRequires:  pkgconfig(gstreamer-1.0) >= 1.24
BuildRequires:  pkgconfig(gstreamer-base-1.0)
BuildRequires:  pkgconfig(gstreamer-video-1.0)
BuildRequires:  pkgconfig(gstreamer-audio-1.0)
BuildRequires:  pkgconfig(gstreamer-pbutils-1.0)
BuildRequires:  pkgconfig(gstreamer-app-1.0)
BuildRequires:  pkgconfig(gstreamer-play-1.0)
BuildRequires:  pkgconfig(gstreamer-plugins-base-1.0)
BuildRequires:  pkgconfig(openssl)
BuildRequires:  pkgconfig(sqlite3)
BuildRequires:  desktop-file-utils

Requires:       hicolor-icon-theme
Requires:       gtk4
Requires:       libadwaita
Requires:       webkitgtk4
Requires:       gstreamer
Requires:       gstreamer-plugins-base
Requires:       gstreamer-plugins-good
Requires:       gstreamer-plugins-bad
Requires:       gstreamer-plugins-libav
Requires:       sqlite-libs
Requires:       openssl-libs
Requires:       yt-dlp
Requires:       nodejs
Recommends:     ffmpeg

%description
Mixtapes is a cross-platform desktop application for streaming YouTube Music,
built with GTK4, Libadwaita and GStreamer. The codebase was rewritten from
Python to Rust in October 2026 ("Rustification of Mixtapes").

Compiled specifically for the Nexus repository via automated Git snapshot.

%prep
%autosetup -n Mixtapes-%{commit}

%build
export CARGO_NET_OFFLINE=true
export RUSTFLAGS="%{build_rustflags}"
cargo build --release --frozen --offline --bin mixtapes

%install
install -d -m 0755 %{buildroot}%{_bindir}
install -Dm755 target/release/mixtapes %{buildroot}%{_bindir}/mixtapes
ln -s mixtapes %{buildroot}%{_bindir}/muse

desktop-file-install --dir %{buildroot}%{_datadir}/applications \
    com.pocoguy.Muse.desktop

mkdir -p %{buildroot}%{_metainfodir}
install -Dm644 com.pocoguy.Muse.metainfo.xml \
    %{buildroot}%{_metainfodir}/com.pocoguy.Muse.metainfo.xml

install -Dm644 assets/icons/hicolor/scalable/apps/com.pocoguy.Muse.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/com.pocoguy.Muse.svg

find %{buildroot} \( -path '*/resources/app-update.yml' -o -path '*/resources/package-type' \) -delete 2>/dev/null || true
%check
desktop-file-validate %{buildroot}%{_datadir}/applications/com.pocoguy.Muse.desktop

%files
%license LICENSE
%doc README.md
%{_bindir}/mixtapes
%{_bindir}/muse
%{_datadir}/applications/com.pocoguy.Muse.desktop
%{_metainfodir}/com.pocoguy.Muse.metainfo.xml
%{_datadir}/icons/hicolor/scalable/apps/com.pocoguy.Muse*.svg

%changelog
