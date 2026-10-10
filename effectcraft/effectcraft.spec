%global debug_package %{nil}
Name:           effectcraft
Version:        0.7.0
Release:        0
Summary:        Motion graphics/VFX - clean-room After Effects in pure Rust
License:        MIT OR Apache-2.0
Group:          Productivity/Graphics/Other
URL:            https://github.com/storytold/effectcraft
Source0:        https://github.com/storytold/effectcraft/releases/download/v0.7.0/effectcraft-0.7.0-linux-x86_64.rpm
BuildRequires:  cpio
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
# Runtime mapping: upstream's RPM Requires are Fedora names
# (alsa-lib -> libasound2, libxkbcommon -> libxkbcommon0, boolean
# vulkan-loader/libglvnd-egl). TW's EGL/GL provider is the libglvnd
# package (verified in TW repodata; no libEGL1 exists).
Requires:       hicolor-icon-theme
Requires:       libasound2
Requires:       libgcc_s1
Requires:       libglvnd
Requires:       libvulkan1
Requires:       libxkbcommon0
ExclusiveArch:  x86_64

%description
EffectCraft: motion graphics and visual effects - a clean-room Adobe
After Effects reimplementation in pure Rust.

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required for pre-built binaries

%install
install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 usr/bin/effectcraft usr/bin/effectcraft-cli %{buildroot}%{_bindir}/

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/metainfo %{buildroot}%{_datadir}/
cp -a usr/share/mime %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.effectcraft.desktop

%files
%license %{_datadir}/doc/effectcraft/LICENSE-APACHE
%license %{_datadir}/doc/effectcraft/LICENSE-MIT
%dir %{_datadir}/doc/effectcraft
%doc %{_datadir}/doc/effectcraft/README.md
%{_bindir}/effectcraft
%{_bindir}/effectcraft-cli
%{_datadir}/applications/ai.storyteller.effectcraft.desktop
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.effectcraft.*
%{_datadir}/metainfo/ai.storyteller.effectcraft.metainfo.xml
%{_datadir}/mime/packages/ai.storyteller.effectcraft.xml

%changelog
