%global debug_package %{nil}
%global __requires_exclude_from ^/opt/concat-unstable/.*$
%global __provides_exclude_from ^/opt/concat-unstable/.*$
%global commit          f0c0169628c61de7311f7fc15ee5be82dd611d2e
%global shortcommit     f0c0169
%global gitdate         20261028102543
%global base_version    0.2.8
Name:           concat-unstable
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        Free and open source video editor (main-branch snapshot)
License:        AGPL-3.0-or-later
Group:          Productivity/Multimedia/Video/Editors and Convertors
URL:            https://github.com/jub0t/concat
Source0:        %{name}-%{version}.tar.gz
BuildRequires:  Mesa-libGL-devel
BuildRequires:  alsa-devel
BuildRequires:  cargo
BuildRequires:  cmake
BuildRequires:  desktop-file-utils
BuildRequires:  fontconfig-devel
BuildRequires:  freetype2-devel
BuildRequires:  gcc-c++
BuildRequires:  gtk3-devel
BuildRequires:  hicolor-icon-theme
BuildRequires:  libclang13
BuildRequires:  libxkbcommon-devel
BuildRequires:  make
BuildRequires:  pkgconf
BuildRequires:  pkgconfig
BuildRequires:  pkgconfig(openssl)
Requires:       Mesa-libGL1
Requires:       fontconfig
Requires:       gtk3
Requires:       hicolor-icon-theme
Requires:       libasound2
Requires:       libfreetype6
Requires:       libgcc_s1
Requires:       libstdc++6
Requires:       libxkbcommon-x11-0
Requires:       libxkbcommon0
Recommends:     xdg-desktop-portal
Recommends:     xdg-desktop-portal-gtk
ExclusiveArch:  x86_64

%description
Concat main-branch snapshot: free and open source cross-platform video
editor (timeline editing, effects, transitions, titles, captions and
speech) with FFmpeg underneath and hardware-accelerated preview and
export. Tracks upstream main past the latest release; base version plus
the newest commit show in the package version.

%prep
%autosetup -n concat-%{commit}

%build
export CARGO_NET_OFFLINE=true
export ORT_SKIP_DOWNLOAD=1
export BINDGEN_EXTRA_CLANG_ARGS="-I$(gcc -print-file-name=include)"
export FFMPEG_DIR="%{_builddir}/concat-%{commit}/ffmpeg-dev"
export ORT_LIB_LOCATION="%{_builddir}/concat-%{commit}/onnxlib"
export ORT_PREFER_DYNAMIC_LINK=1
export SKIA_BINARIES_URL="file://%{_builddir}/concat-%{commit}/skia-cache/skia-binaries-b7f043e0b1e2a850e702-x86_64-unknown-linux-gnu-ganesh-gl-jpegd-jpege-pdf-vulkan.tar.gz"
export SHERPA_ONNX_ARCHIVE_DIR="%{_builddir}/concat-%{commit}/sherpa-cache"
export RUSTFLAGS="-C link-arg=-Wl,-rpath,\$ORIGIN/lib -C link-arg=-Wl,--disable-new-dtags"
cd src && cargo build --offline --frozen --release --bin concat

%install
install -d -m 0755 %{buildroot}/opt/concat-unstable/lib
install -m 0755 src/target/release/concat %{buildroot}/opt/concat-unstable/concat-unstable
cp -a ffmpeg-dev/lib/lib*.so* %{buildroot}/opt/concat-unstable/lib/
cp -a onnxlib/libonnxruntime.so* %{buildroot}/opt/concat-unstable/lib/

install -d -m 0755 %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/concat-unstable <<'EOF'
#!/bin/sh
exec /opt/concat-unstable/concat-unstable "$@"
EOF
chmod 0755 %{buildroot}%{_bindir}/concat-unstable

install -d -m 0755 %{buildroot}%{_datadir}/applications
cat > %{buildroot}%{_datadir}/applications/concat-unstable.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Concat (Unstable)
Comment=Video editor - main branch snapshot
Exec=/usr/bin/concat-unstable %U
Icon=concat-unstable
Terminal=false
Categories=AudioVideo;Video;
EOF

install -d -m 0755 %{buildroot}%{_datadir}/icons/hicolor/256x256/apps
install -m 0644 assets/icons/concat_logo_256.png \
    %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/concat-unstable.png

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/concat-unstable.desktop

%files
%license LICENSE
%{_bindir}/concat-unstable
%{_datadir}/applications/concat-unstable.desktop
%{_datadir}/icons/hicolor/256x256/apps/concat-unstable.png
/opt/concat-unstable/

%changelog
