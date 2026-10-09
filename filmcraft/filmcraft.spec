%global debug_package %{nil}
Name:           filmcraft
Version:        0.4.0
Release:        0
Summary:        Video editor - clean-room Premiere Pro in pure Rust
License:        MIT OR Apache-2.0
Group:          Productivity/Multimedia/Video/Editors
URL:            https://github.com/storytold/filmcraft
Source0:        https://github.com/storytold/filmcraft/releases/download/v%{version}/filmcraft-%{version}-linux-x86_64.rpm
BuildRequires:  cpio
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
# Runtime mapping: upstream's RPM Requires are Fedora names
# (alsa-lib -> libasound2, libxkbcommon -> libxkbcommon0, boolean
# vulkan-loader/libglvnd-egl). Payload ELF NEEDED is libc/m/gcc plus
# libasound (audio engine); Vulkan/GL loaders are dlopened at runtime.
# TW's EGL/GL provider is the libglvnd package (verified in TW repodata;
# there is no libEGL1), Vulkan is libvulkan1 - both listed explicitly.
Requires:       hicolor-icon-theme
Requires:       libasound2
Requires:       libgcc_s1
Requires:       libglvnd
Requires:       libvulkan1
Requires:       libxkbcommon0
ExclusiveArch:  x86_64

%description
FilmCraft: a clean-room Adobe Premiere Pro reimplementation in pure Rust.
Timeline video editing with effects and export.

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required for pre-built binaries

%install
install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 usr/bin/filmcraft usr/bin/filmcraft-cli %{buildroot}%{_bindir}/

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/metainfo %{buildroot}%{_datadir}/
cp -a usr/share/mime %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.filmcraft.desktop

%files
%license %{_datadir}/doc/filmcraft/LICENSE-APACHE
%license %{_datadir}/doc/filmcraft/LICENSE-MIT
%doc %{_datadir}/doc/filmcraft/README.md
%doc %{_datadir}/doc/filmcraft/OFL-*.txt
%{_bindir}/filmcraft
%{_bindir}/filmcraft-cli
%{_datadir}/applications/ai.storyteller.filmcraft.desktop
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.filmcraft.*
%{_datadir}/metainfo/ai.storyteller.filmcraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.filmcraft.xml

%changelog
