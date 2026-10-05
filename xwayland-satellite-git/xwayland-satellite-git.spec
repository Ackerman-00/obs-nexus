# These will be automatically populated by update.sh
%global commit          b5690b56d749526a05db9b9268d58bf8f700957f
%global shortcommit     b5690b5
%global gitdate         20260930121453
Name:           xwayland-satellite-git
Version:        0.8.3+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        Rootless Xwayland integration for Wayland compositors (Nexus Optimized)
License:        MPL-2.0
Group:          System/GUI/Other
URL:            https://github.com/Supreeeme/xwayland-satellite
Source0:        xwayland-satellite-%{shortcommit}.tar.gz
Source1:        vendor.tar.xz
Source2:        cargo_config
BuildRequires:  cargo-packaging
BuildRequires:  clang
# NOTE: no clang-devel/llvm-devel: upstream has no bindgen and no C code
# (build-deps are only anyhow + vergen-gitcl); libclang headers and the
# LLVM C API are unused. clang-devel pulls the versioned clang23-devel
# chain which is unresolvable on Slowroll (clang-tools skew); plain
# clang (as in niri-git) resolves on both codestreams.
BuildRequires:  gcc-c++
BuildRequires:  pkgconfig
BuildRequires:  systemd-rpm-macros
BuildRequires:  pkgconfig(fontconfig)
BuildRequires:  pkgconfig(wayland-client)
BuildRequires:  pkgconfig(wayland-cursor)
BuildRequires:  pkgconfig(wayland-server)
BuildRequires:  pkgconfig(xcb)
BuildRequires:  pkgconfig(xcb-cursor)
Requires:       google-opensans-fonts
# OpenSUSE specific naming architecture
Requires:       xwayland
Conflicts:      xwayland-satellite
Provides:       xwayland-satellite = %{version}
ExclusiveArch:  x86_64 aarch64

%description
xwayland-satellite grants rootless Xwayland integration to any Wayland
compositor implementing xdg_wm_base and viewporter. This package tracks
the bleeding-edge master branch.

%prep
# Extract Source0 and Source1 smoothly
%autosetup -n xwayland-satellite-%{commit} -p1 -a1

# Inject offline cargo config securely
mkdir -p .cargo
cp %{SOURCE2} .cargo/config

# Dynamically fix the executable path in the systemd unit using system path macros
sed -i 's|%{_prefix}/local/bin|%{_bindir}|g' resources/xwayland-satellite.service

# Remove vendored decoration font if it exists in the current git tree to save weight
rm -f OpenSans-Regular.ttf

%build
# Arch adds fat-lto-objects to ensure proper static linking across dependencies
export CFLAGS="%{optflags} -ffat-lto-objects"
export CXXFLAGS="%{optflags} -ffat-lto-objects"

# Inject openSUSE native system optimization/rust flags while honoring your offline layout
export RUSTFLAGS="%{build_rustflags}"
cargo build --offline --release --features systemd,fontconfig

%install
install -Dpm0755 target/release/xwayland-satellite -t %{buildroot}%{_bindir}
install -Dpm0644 resources/xwayland-satellite.service -t %{buildroot}%{_userunitdir}

%post
%systemd_user_post xwayland-satellite.service

%preun
%systemd_user_preun xwayland-satellite.service

%postun
%systemd_user_postun xwayland-satellite.service

%files
%license LICENSE
%doc README.md
%{_bindir}/xwayland-satellite

# Explicitly own user systemd directories to satisfy strict Tumbleweed packaging constraints
%dir %{_userunitdir}
%{_userunitdir}/xwayland-satellite.service

%changelog
