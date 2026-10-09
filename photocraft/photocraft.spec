%global debug_package %{nil}
Name:           photocraft
Version:        0.5.0
Release:        0
Summary:        Photo editor - clean-room Photoshop in pure Rust
License:        MIT OR Apache-2.0
Group:          Productivity/Graphics/Editors
URL:            https://github.com/storytold/photocraft
Source0:        https://github.com/storytold/photocraft/releases/download/v%{version}/photocraft-%{version}-linux-x86_64.rpm
BuildRequires:  cpio
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
# Runtime mapping: upstream's RPM Requires are ALREADY correct soname
# form (verified against TW repodata providers), including the X11/
# wayland/xkbcommon-x11 GUI set this app links beyond dlopen. Kept
# verbatim on purpose; only libgcc_s (NEEDED) and the icon theme are
# added. Bundled payload has no private .so needing excludes.
Requires:       hicolor-icon-theme
Requires:       libX11-xcb.so.1()(64bit)
Requires:       libX11.so.6()(64bit)
Requires:       libXcursor.so.1()(64bit)
Requires:       libXi.so.6()(64bit)
Requires:       libgcc_s1
Requires:       libvulkan.so.1()(64bit)
Requires:       libEGL.so.1()(64bit)
Requires:       libwayland-client.so.0()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon-x11.so.0()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
ExclusiveArch:  x86_64

%description
PhotoCraft: a clean-room Adobe Photoshop reimplementation in pure Rust.
Layer-based photo editing and digital painting.

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required for pre-built binaries

%install
install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 usr/bin/photocraft usr/bin/photocraft-cli %{buildroot}%{_bindir}/

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/metainfo %{buildroot}%{_datadir}/
cp -a usr/share/mime %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.photocraft.desktop

%files
%license %{_datadir}/doc/photocraft/LICENSE-APACHE
%license %{_datadir}/doc/photocraft/LICENSE-MIT
%doc %{_datadir}/doc/photocraft/OFL-*.txt
%doc %{_datadir}/doc/photocraft/README.md
%{_bindir}/photocraft
%{_bindir}/photocraft-cli
%{_datadir}/applications/ai.storyteller.photocraft.desktop
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.photocraft.png
%{_datadir}/metainfo/ai.storyteller.photocraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.photocraft.xml

%changelog
