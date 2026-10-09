%global debug_package %{nil}
Name:           cadcraft
Version:        0.3.0
Release:        0
Summary:        CAD/drafting - clean-room AutoCAD-style app in pure Rust
License:        MIT OR Apache-2.0
Group:          Productivity/Graphics/CAD
URL:            https://github.com/storytold/cadcraft
Source0:        https://github.com/storytold/cadcraft/releases/download/v%{version}/cadcraft-%{version}-linux-x86_64.rpm
BuildRequires:  cpio
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
# Runtime mapping: upstream's RPM Requires are Fedora names
# (libxkbcommon -> libxkbcommon0, boolean vulkan-loader/libglvnd-egl).
# Payload ELF NEEDED is libc/m/gcc only; Vulkan/GL loaders are dlopened
# at runtime, so both providers are listed explicitly (no boolean).
Requires:       hicolor-icon-theme
Requires:       libgcc_s1
Requires:       libglvnd
Requires:       libvulkan1
Requires:       libxkbcommon0
ExclusiveArch:  x86_64

%description
CADCraft: computer-aided design and drafting - an open-source, clean-room
AutoCAD-style app in pure Rust. Draft, dimension and plot 2D drawings;
open DXF and DWG files.

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required for pre-built binaries

%install
install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 usr/bin/cadcraft usr/bin/cadcraft-cli %{buildroot}%{_bindir}/

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/metainfo %{buildroot}%{_datadir}/
cp -a usr/share/mime %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.cadcraft.desktop

%files
%license %{_datadir}/doc/cadcraft/LICENSE-APACHE
%license %{_datadir}/doc/cadcraft/LICENSE-MIT
%doc %{_datadir}/doc/cadcraft/README.md
%{_bindir}/cadcraft
%{_bindir}/cadcraft-cli
%{_datadir}/applications/ai.storyteller.cadcraft.desktop
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.cadcraft.png
%{_datadir}/metainfo/ai.storyteller.cadcraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.cadcraft.xml

%changelog
