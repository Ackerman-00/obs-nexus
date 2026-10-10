%global debug_package %{nil}
Name:           vectorcraft
Version:        0.8.0
Release:        0
Summary:        Vector editor - clean-room Illustrator in pure Rust
License:        MIT OR Apache-2.0
Group:          Productivity/Graphics/Editors
URL:            https://github.com/storytold/vectorcraft
Source0:        https://github.com/storytold/vectorcraft/releases/download/v0.8.0/vectorcraft-0.8.0-linux-x86_64.rpm
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
VectorCraft: a clean-room Adobe Illustrator reimplementation in pure Rust.
Resolution-independent vector illustration and design.

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required for pre-built binaries

%install
install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 usr/bin/vectorcraft usr/bin/vectorcraft-cli %{buildroot}%{_bindir}/

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/metainfo %{buildroot}%{_datadir}/
cp -a usr/share/mime %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.vectorcraft.desktop

%files
%license %{_datadir}/doc/vectorcraft/LICENSE-APACHE
%license %{_datadir}/doc/vectorcraft/LICENSE-MIT
%dir %{_datadir}/doc/vectorcraft
%doc %{_datadir}/doc/vectorcraft/OFL-*.txt
%doc %{_datadir}/doc/vectorcraft/README.md
%{_bindir}/vectorcraft
%{_bindir}/vectorcraft-cli
%{_datadir}/applications/ai.storyteller.vectorcraft.desktop
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.vectorcraft.*
%{_datadir}/metainfo/ai.storyteller.vectorcraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.vectorcraft.xml

%changelog
