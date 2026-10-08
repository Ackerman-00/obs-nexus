# These will be automatically populated by update.sh
%global commit          2c82b77a7116a1241ea2fd41dd008ff00b609aae
%global shortcommit     2c82b77
%global gitdate         20261008063200
Name:           niri-git
Version:        26.04+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        A scrollable-tiling Wayland compositor (Nexus Optimized)
License:        GPL-3.0-or-later
Group:          System/GUI/Other
URL:            https://github.com/niri-wm/niri
# Generated dynamically by GitHub Actions
Source0:        niri-%{shortcommit}.tar.gz
Source1:        vendor.tar.xz
Source2:        cargo_config
BuildRequires:  cargo-packaging
BuildRequires:  clang
BuildRequires:  gcc-c++
BuildRequires:  pkgconfig
BuildRequires:  systemd-rpm-macros
BuildRequires:  pkgconfig(cairo-gobject)
BuildRequires:  pkgconfig(dbus-1)
BuildRequires:  pkgconfig(egl)
BuildRequires:  pkgconfig(gbm)
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  pkgconfig(libdisplay-info)
BuildRequires:  pkgconfig(libinput)
BuildRequires:  pkgconfig(libpipewire-0.3)
BuildRequires:  pkgconfig(libseat)
BuildRequires:  pkgconfig(libudev)
BuildRequires:  pkgconfig(pango)
BuildRequires:  pkgconfig(pangocairo)
BuildRequires:  pkgconfig(pixman-1)
BuildRequires:  pkgconfig(systemd)
BuildRequires:  pkgconfig(wayland-client)
BuildRequires:  pkgconfig(wayland-server)
BuildRequires:  pkgconfig(xkbcommon)
Requires:       Mesa-dri
Requires:       Mesa-libEGL1
Requires:       xdg-desktop-portal
Requires:       xwayland-satellite-git
Recommends:     gnome-keyring
Recommends:     xdg-desktop-portal-gnome
Recommends:     xdg-desktop-portal-gtk
Conflicts:      niri
Provides:       niri = %{version}
Provides:       wayland-compositor
ExclusiveArch:  x86_64 aarch64

%description
A scrollable-tiling Wayland compositor.
Compiled specifically for the Nexus repository via automated Git snapshot. Stripped of all secondary GUI bloat and synchronized with our custom Xwayland bridge for peak performance.

%prep
# Extract Source0 and Source1 smoothly
%autosetup -n niri-%{commit} -p1 -a1

# Inject offline cargo configuration safely
mkdir -p .cargo
cp %{SOURCE2} .cargo/config

%build
# Set the commit string for the binary output metadata
export NIRI_BUILD_COMMIT="%{shortcommit}"

# Arch adds fat-lto-objects to ensure proper static linking across dependencies
export CFLAGS="%{optflags} -ffat-lto-objects"
export CXXFLAGS="%{optflags} -ffat-lto-objects"

# Inject openSUSE native system optimization/rust flags while honoring your offline layout
export RUSTFLAGS="%{build_rustflags}"
cargo build --offline --release --features default

# Generate shell completions safely by initializing a mocked runtime environment
export XDG_RUNTIME_DIR=$(mktemp -d)
target/release/niri completions bash > ./niri.bash
target/release/niri completions fish > ./niri.fish
target/release/niri completions zsh > ./_niri

%install
# Install the core binaries
install -Dpm0755 target/release/niri -t %{buildroot}%{_bindir}
install -Dpm0755 resources/niri-session -t %{buildroot}%{_bindir}

# Install standard Wayland session and systemd configurations
install -Dpm0644 resources/niri.desktop -t %{buildroot}%{_datadir}/wayland-sessions
install -Dpm0644 resources/niri-portals.conf -t %{buildroot}%{_datadir}/xdg-desktop-portal
install -Dpm0644 resources/niri.service -t %{buildroot}%{_userunitdir}
install -Dpm0644 resources/niri-shutdown.target -t %{buildroot}%{_userunitdir}

# Install completions matching openSUSE downstream paths
install -Dpm0644 niri.bash %{buildroot}%{_datadir}/bash-completion/completions/niri
install -Dpm0644 niri.fish %{buildroot}%{_datadir}/fish/vendor_completions.d/niri.fish
install -Dpm0644 _niri %{buildroot}%{_datadir}/zsh/site-functions/_niri

%files
%license LICENSE
%doc README.md
%doc resources/default-config.kdl
%{_bindir}/niri
%{_bindir}/niri-session

# Explicitly own user systemd directories to satisfy strict RPMLINT rules
%dir %{_userunitdir}
%{_userunitdir}/niri.service
%{_userunitdir}/niri-shutdown.target

# Explicit directory ownership for session files
%dir %{_datadir}/wayland-sessions
%{_datadir}/wayland-sessions/niri.desktop
%dir %{_datadir}/xdg-desktop-portal
%{_datadir}/xdg-desktop-portal/niri-portals.conf

# Complete shell completion ownership architecture
%dir %{_datadir}/bash-completion
%dir %{_datadir}/bash-completion/completions
%{_datadir}/bash-completion/completions/niri

%dir %{_datadir}/fish
%dir %{_datadir}/fish/vendor_completions.d
%{_datadir}/fish/vendor_completions.d/niri.fish

%dir %{_datadir}/zsh
%dir %{_datadir}/zsh/site-functions
%{_datadir}/zsh/site-functions/_niri

%changelog
