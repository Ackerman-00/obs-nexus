%global debug_package %{nil}
Name:           pdfcraft
Version:        0.5.0
Release:        0
Summary:        Document viewer/editor - clean-room Acrobat in pure Rust
License:        MIT OR Apache-2.0
Group:          Productivity/Office/Other
URL:            https://github.com/storytold/pdfcraft
Source0:        https://github.com/storytold/pdfcraft/releases/download/v0.5.0/pdfcraft-0.5.0-linux-x86_64.rpm
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
PDFCraft: a clean-room Adobe Acrobat reimplementation in pure Rust.
View, annotate and export PDF documents.

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required for pre-built binaries

%install
install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 usr/bin/pdfcraft usr/bin/pdfcraft-cli %{buildroot}%{_bindir}/

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/metainfo %{buildroot}%{_datadir}/
cp -a usr/share/mime %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.pdfcraft.desktop

%files
%license %{_datadir}/doc/pdfcraft/LICENSE-APACHE
%license %{_datadir}/doc/pdfcraft/LICENSE-MIT
%dir %{_datadir}/doc/pdfcraft
%doc %{_datadir}/doc/pdfcraft/OFL-*.txt
%doc %{_datadir}/doc/pdfcraft/README.md
%{_bindir}/pdfcraft
%{_bindir}/pdfcraft-cli
%{_datadir}/applications/ai.storyteller.pdfcraft.desktop
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.pdfcraft.*
%{_datadir}/metainfo/ai.storyteller.pdfcraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.pdfcraft.xml

%changelog
