%global debug_package %{nil}
Name:           designcraft
Version:        0.4.0
Release:        0
Summary:        Page layout/publishing - clean-room InDesign in pure Rust
License:        MIT OR Apache-2.0
Group:          Productivity/Graphics/Editors
URL:            https://github.com/storytold/designcraft
Source0:        https://github.com/storytold/designcraft/releases/download/v%{version}/designcraft-%{version}-linux-x86_64.rpm
BuildRequires:  cpio
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
# Runtime mapping: upstream's RPM Requires are Fedora names
# (libxkbcommon -> libxkbcommon0, boolean vulkan-loader/libglvnd-egl).
# Payload ELF NEEDED is libc/m/gcc only; Vulkan/GL loaders are dlopened
# at runtime. TW's EGL/GL provider is the libglvnd package (verified in
# TW repodata; no libEGL1 exists), Vulkan is libvulkan1.
Requires:       hicolor-icon-theme
Requires:       libgcc_s1
Requires:       libglvnd
Requires:       libvulkan1
Requires:       libxkbcommon0
ExclusiveArch:  x86_64

%description
DesignCraft: page layout and publishing - a clean-room Adobe InDesign
reimplementation in pure Rust.

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required for pre-built binaries

%install
install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 usr/bin/designcraft usr/bin/designcraft-cli %{buildroot}%{_bindir}/

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/metainfo %{buildroot}%{_datadir}/
cp -a usr/share/mime %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.designcraft.desktop

%files
%license %{_datadir}/doc/designcraft/LICENSE-APACHE
%license %{_datadir}/doc/designcraft/LICENSE-MIT
%doc %{_datadir}/doc/designcraft/OFL-*.txt
%doc %{_datadir}/doc/designcraft/README.md
%{_bindir}/designcraft
%{_bindir}/designcraft-cli
%{_datadir}/applications/ai.storyteller.designcraft.desktop
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.designcraft.*
%{_datadir}/metainfo/ai.storyteller.designcraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.designcraft.xml

%changelog
