%global debug_package %{nil}
# NOTE: upstream repo is storytold/craft-launcher but every artifact
# (rpm/deb/AppImage name, binary, desktop file, Cargo crates) is called
# artcraft-launcher - the package follows the artifact name.
Name:           artcraft-launcher
Version:        0.2.0
Release:        0
Summary:        App launcher for the Craft suite
License:        MIT OR Apache-2.0
Group:          System/Packages
URL:            https://github.com/storytold/craft-launcher
Source0:        https://github.com/storytold/craft-launcher/releases/download/v0.2.0/artcraft-launcher-0.2.0-linux-x86_64.rpm
BuildRequires:  cpio
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
# Runtime mapping: upstream's RPM Requires are ALREADY correct soname
# form (verified against TW repodata providers), like photocraft's.
# Kept verbatim on purpose; only libgcc_s (NEEDED) and the icon theme
# are added. Payload has no bundled .so needing excludes.
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
ArtCraft Launcher: the app launcher for the Craft suite of clean-room
creative tools (CAD, audio, video, photo, vector, PDF, design).

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build
# No compilation required for pre-built binaries

%install
install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 usr/bin/artcraft-launcher %{buildroot}%{_bindir}/

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/metainfo %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/ai.storyteller.artcraft-launcher.desktop

%files
%license %{_datadir}/doc/artcraft-launcher/LICENSE-APACHE
%license %{_datadir}/doc/artcraft-launcher/LICENSE-MIT
%dir %{_datadir}/doc/artcraft-launcher
%doc %{_datadir}/doc/artcraft-launcher/ATTRIBUTION.md
%doc %{_datadir}/doc/artcraft-launcher/NOTICE
%doc %{_datadir}/doc/artcraft-launcher/README.md
%{_bindir}/artcraft-launcher
%{_datadir}/applications/ai.storyteller.artcraft-launcher.desktop
%{_datadir}/icons/hicolor/*/apps/ai.storyteller.artcraft-launcher.png
%{_datadir}/icons/hicolor/scalable/apps/ai.storyteller.artcraft-launcher.svg
%{_datadir}/metainfo/ai.storyteller.artcraft-launcher.metainfo.xml

%changelog
