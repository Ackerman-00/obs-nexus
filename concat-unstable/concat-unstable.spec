%global debug_package %{nil}
%global __requires_exclude_from ^/opt/concat-unstable/.*$
%global __provides_exclude_from ^/opt/concat-unstable/.*$
%global commit          4d3b0a14e59452c62b1ad3876593cfb92da1671d
%global shortcommit     4d3b0a1
%global gitdate         20261126123453
%global base_version    0.2.12
Name:           concat-unstable
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        Free and open source video editor (main-branch snapshot)
License:        AGPL-3.0-or-later
Group:          Productivity/Multimedia/Video/Editors and Convertors
URL:            https://github.com/jub0t/concat
Source0:        %{name}-%{version}.tar.gz
BuildRequires:  alsa-devel
BuildRequires:  cargo
BuildRequires:  cmake
BuildRequires:  desktop-file-utils
BuildRequires:  fontconfig-devel
BuildRequires:  gcc-c++
BuildRequires:  hicolor-icon-theme
BuildRequires:  libclang13
BuildRequires:  make
BuildRequires:  pkgconf
BuildRequires:  pkgconfig
BuildRequires:  pkgconfig(openssl)
Requires:       Mesa-libEGL1
Requires:       Mesa-libGL1
Requires:       fontconfig
Requires:       hicolor-icon-theme
Requires:       libX11-6
Requires:       libX11-xcb1
Requires:       libXcursor1
Requires:       libXi6
Requires:       libXrender1
Requires:       libasound2
Requires:       libdbus-1-3
Requires:       libfreetype6
Requires:       libgcc_s1
Requires:       libstdc++6
Requires:       libwayland-client0
Requires:       libwayland-egl1
Requires:       libxkbcommon-x11-0
Requires:       libxkbcommon0
Recommends:     libayatana-appindicator3.so.1()(64bit)
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
# ort-sys copy-dylibs symlinks into target/<profile>/{examples,deps}; cargo 1.100 no longer creates them
ortlink=src/vendor/ort-sys/build/dynamic_link.rs
grep -q 'create_dir_all(&out_dir)' "$ortlink" || sed -i 's|^\(\s*\)for out_dir in \[out_dir.to_path_buf(), out_dir.join("examples"), out_dir.join("deps")\] {|&\n\t\tlet _ = fs::create_dir_all(\&out_dir);|' "$ortlink"
grep -q 'create_dir_all(&out_dir)' "$ortlink" || { echo "ort-sys dynamic_link.rs layout changed; refusing to build an unpatched payload"; exit 1; }
python3 -I - <<'PY'
import hashlib, json
p = 'src/vendor/ort-sys/build/dynamic_link.rs'
j = 'src/vendor/ort-sys/.cargo-checksum.json'
d = json.load(open(j))
key = next((k for k in d.get('files', {}) if k.endswith('build/dynamic_link.rs')), None)
d.setdefault('files', {})[key or 'build/dynamic_link.rs'] = hashlib.sha256(open(p, 'rb').read()).hexdigest()
json.dump(d, open(j, 'w'))
PY

%build
export CARGO_NET_OFFLINE=true
export ORT_SKIP_DOWNLOAD=1
export BINDGEN_EXTRA_CLANG_ARGS="-I$(gcc -print-file-name=include)"
export FFMPEG_DIR="%{_builddir}/concat-%{commit}/ffmpeg-dev"
export ORT_LIB_LOCATION="%{_builddir}/concat-%{commit}/onnxlib"
export ORT_PREFER_DYNAMIC_LINK=1
export SKIA_BINARIES_URL="file://%{_builddir}/concat-%{commit}/skia-cache/skia-binaries-b7f043e0b1e2a850e702-x86_64-unknown-linux-gnu-ganesh-gl-jpegd-jpege-pdf-vulkan.tar.gz"
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
Exec=%{_bindir}/concat-unstable %U
Icon=concat-unstable
Terminal=false
Categories=AudioVideo;Video;
EOF

install -d -m 0755 %{buildroot}%{_datadir}/icons/hicolor/256x256/apps
install -m 0644 assets/icons/concat_logo_256.png \
    %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/concat-unstable.png

find %{buildroot} \( -path '*/resources/app-update.yml' -o -path '*/resources/package-type' \) -delete 2>/dev/null || true

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/concat-unstable.desktop

%files
%license LICENSE
%{_bindir}/concat-unstable
%{_datadir}/applications/concat-unstable.desktop
%{_datadir}/icons/hicolor/256x256/apps/concat-unstable.png
/opt/concat-unstable/

%changelog
