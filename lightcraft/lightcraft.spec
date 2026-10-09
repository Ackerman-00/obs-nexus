%global debug_package %{nil}
Name:           lightcraft
Version:        0.4.0
Release:        0
Summary:        Photo manager - clean-room Lightroom in pure Rust
License:        MIT OR Apache-2.0
Group:          Productivity/Graphics/Photography
URL:            https://github.com/storytold/lightcraft
Source0:        https://github.com/storytold/lightcraft/releases/download/v%{version}/lightcraft-%{version}-linux-x86_64.rpm
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
LightCraft: a clean-room Adobe Lightroom reimplementation in pure Rust.
Organize, develop and export photographs.

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required for pre-built binaries

%install
install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 usr/bin/lightcraft usr/bin/lightcraft-cli %{buildroot}%{_bindir}/

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/metainfo %{buildroot}%{_datadir}/
cp -a usr/share/mime %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.lightcraft.desktop

%files
%license %{_datadir}/doc/lightcraft/LICENSE-APACHE
%license %{_datadir}/doc/lightcraft/LICENSE-MIT
%doc %{_datadir}/doc/lightcraft/NOTICE
%doc %{_datadir}/doc/lightcraft/OFL-*.txt
%doc %{_datadir}/doc/lightcraft/README.md
%{_bindir}/lightcraft
%{_bindir}/lightcraft-cli
%{_datadir}/applications/ai.storyteller.lightcraft.desktop
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.lightcraft.*
%{_datadir}/metainfo/ai.storyteller.lightcraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.lightcraft.xml

%changelog
