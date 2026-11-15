%global commit          936473c9d804da3999ef191f8febaabacd1834b7
%global shortcommit     936473c
%global gitdate         20261115034454
%global base_version    1.7.0
Name:           noctalia-greeter
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        Login greeter for greetd with the Noctalia Shell look and feel
License:        MIT AND Apache-2.0
Group:          System/Boot/Other
URL:            https://github.com/noctalia-dev/noctalia-greeter
Source0:        noctalia-greeter-%{shortcommit}.tar.gz
Source3:        stb_image_resize2-git-2026-11-01-703100c5f8a0.h
# sha256: 6965f5c5c50aa1d5af670148814ce9559d5d06328099437686aa3d934708e04b
Source1:        https://raw.githubusercontent.com/google/wuffs/a14745aa458fd2b2785034efa04eab3c7b5b91e0/LICENSE-APACHE
# sha256: 0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594
Source2:        https://raw.githubusercontent.com/google/wuffs/a14745aa458fd2b2785034efa04eab3c7b5b91e0/LICENSE-MIT
# sha256: bb811a4b485eac3caeb8bdc58bbafb355fbcb6116010a7ea9179e5c70b0bc878

BuildRequires:  meson >= 1.3
BuildRequires:  gcc-c++
BuildRequires:  diffutils
BuildRequires:  libinput-devel
BuildRequires:  wlroots-devel
BuildRequires:  pkgconfig(wayland-scanner)
BuildRequires:  pkgconfig(glesv2)
BuildRequires:  pkgconfig(cairo)
BuildRequires:  pkgconfig(cairo-ft)
BuildRequires:  pkgconfig(egl)
BuildRequires:  pkgconfig(fontconfig)
BuildRequires:  pkgconfig(freetype2)
BuildRequires:  pkgconfig(gio-2.0)
BuildRequires:  pkgconfig(glib-2.0)
BuildRequires:  pkgconfig(gobject-2.0)
BuildRequires:  pkgconfig(librsvg-2.0)
BuildRequires:  pkgconfig(libjxl)
BuildRequires:  pkgconfig(libjxl_threads)
BuildRequires:  pkgconfig(libwebp)
BuildRequires:  pkgconfig(libxml-2.0)
BuildRequires:  pkgconfig(nlohmann_json)
BuildRequires:  pkgconfig(pango)
BuildRequires:  pkgconfig(pangocairo)
BuildRequires:  pkgconfig(pangoft2)
BuildRequires:  pkgconfig(tomlplusplus)
BuildRequires:  pkgconfig(wayland-client)
BuildRequires:  pkgconfig(wayland-egl)
BuildRequires:  pkgconfig(wayland-protocols) >= 1.39
BuildRequires:  pkgconfig(wayland-server)
BuildRequires:  pkgconfig(xkbcommon)
BuildRequires:  pkgconfig(libudev)
BuildRequires:  systemd-rpm-macros

Requires:       dbus-1
Requires:       /usr/bin/dbus-run-session
Requires:       greetd
Recommends:     polkit

%description
A minimal login greeter for greetd that matches the look and feel of Noctalia
Shell, built with wlroots. Compiled specifically for the Nexus repository
via automated Git snapshot.

%prep
%autosetup -n noctalia-greeter-%{commit}
mkdir -p stb
cp %{SOURCE3} stb/stb_image_resize2.h

%build
export CFLAGS="-I%{_builddir}/noctalia-greeter-%{commit} -I%{_builddir}/noctalia-greeter-%{commit}/stb $CFLAGS"
export CXXFLAGS="-I%{_builddir}/noctalia-greeter-%{commit} -I%{_builddir}/noctalia-greeter-%{commit}/stb $CXXFLAGS"
%meson -Db_pie=true
%meson_build

%install
%meson_install
rm -f %{buildroot}%{_tmpfilesdir}/noctalia-greeter.conf

install -d %{buildroot}%{_licensedir}/%{name}/third_party
install -d %{buildroot}%{_licensedir}/%{name}/third_party/wuffs
install -p -m 0644 %{SOURCE1} %{buildroot}%{_licensedir}/%{name}/third_party/wuffs/LICENSE-APACHE
install -p -m 0644 %{SOURCE2} %{buildroot}%{_licensedir}/%{name}/third_party/wuffs/LICENSE-MIT

find third_party -type f \( -name "LICENSE*" -o -name "COPYING*" -o -name "NOTICE*" \) | while read -r file; do
    dest_dir="%{buildroot}%{_licensedir}/%{name}/$(dirname "$file")"
    install -d "$dest_dir"
    install -p -m 0644 "$file" "$dest_dir/"
done

find %{buildroot} \( -path '*/resources/app-update.yml' -o -path '*/resources/package-type' \) -delete 2>/dev/null || true
%check
%meson_test

%files
%doc README.md
%license LICENSE
%{_licensedir}/%{name}/third_party/
%{_bindir}/%{name}
%{_bindir}/%{name}-apply-appearance
%{_bindir}/%{name}-compositor
%{_bindir}/%{name}-print-greetd-config
%{_bindir}/%{name}-session
%{_bindir}/%{name}-xsession
%{_datadir}/%{name}/*
%{_datadir}/polkit-1/actions/org.noctalia.greeter.apply-appearance.policy

%post
if [ "$1" -eq 1 ]; then
    echo
    echo "================================================================"
    echo "  noctalia-greeter is installed but NOT enabled yet."
    echo
    echo "  1. Run the system setup script (PAM patch, state dir, config):"
    echo "    sudo /usr/share/noctalia-greeter/setup_greeter_system.sh"
    echo
    echo "  2. Point greetd at the greeter - /etc/greetd/config.toml:"
    echo "    [default_session]"
    echo "    command = \"/usr/bin/noctalia-greeter-session\""
    echo "    user = \"greetd\""
    echo
    echo "  3. Enable and start it:"
    echo "    sudo systemctl enable --now greetd"
    echo
    echo "  Tip: user avatars on the login screen need accountsservice:"
    echo "    sudo zypper install accountsservice"
    echo "================================================================"
fi

%changelog
