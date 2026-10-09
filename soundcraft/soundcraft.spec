%global debug_package %{nil}
Name:           soundcraft
Version:        0.3.0
Release:        0
Summary:        Digital audio workstation - clean-room Pro Tools in pure Rust
License:        MIT OR Apache-2.0
Group:          Productivity/Multimedia/Audio
URL:            https://github.com/storytold/soundcraft
Source0:        https://github.com/storytold/soundcraft/releases/download/v%{version}/soundcraft-%{version}-linux-x86_64.rpm
BuildRequires:  cpio
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
# Runtime mapping: upstream's RPM Requires are Fedora names
# (alsa-lib -> libasound2, libxkbcommon -> libxkbcommon0, boolean
# vulkan-loader/libglvnd-egl). Payload ELF NEEDED adds libasound (cpal);
# Vulkan/GL loaders are dlopened at runtime. TW's EGL/GL provider is the
# libglvnd package (verified in TW repodata; no libEGL1 exists).
Requires:       hicolor-icon-theme
Requires:       libasound2
Requires:       libgcc_s1
Requires:       libglvnd
Requires:       libvulkan1
Requires:       libxkbcommon0
ExclusiveArch:  x86_64

%description
SoundCraft: an open-source, clean-room reimplementation of Avid Pro Tools
in pure Rust. Record, edit and mix audio and MIDI.

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required for pre-built binaries

%install
install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 usr/bin/soundcraft usr/bin/soundcraft-cli %{buildroot}%{_bindir}/

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/metainfo %{buildroot}%{_datadir}/
cp -a usr/share/mime %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.soundcraft.desktop

%files
%license %{_datadir}/doc/soundcraft/LICENSE-APACHE
%license %{_datadir}/doc/soundcraft/LICENSE-MIT
%dir %{_datadir}/doc/soundcraft
%doc %{_datadir}/doc/soundcraft/ATTRIBUTION.md
%doc %{_datadir}/doc/soundcraft/NOTICE
%doc %{_datadir}/doc/soundcraft/README.md
%{_bindir}/soundcraft
%{_bindir}/soundcraft-cli
%{_datadir}/applications/ai.storyteller.soundcraft.desktop
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.soundcraft.*
%{_datadir}/metainfo/ai.storyteller.soundcraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.soundcraft.xml

%changelog
