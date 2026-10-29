%global debug_package %{nil}
%global __requires_exclude_from ^/opt/concat/.*$
%global __provides_exclude_from ^/opt/concat/.*$
Name:           concat
Version:        0.2.8
Release:        0
Summary:        Free and open source video editor
License:        AGPL-3.0-or-later
Group:          Productivity/Multimedia/Video/Editors and Convertors
URL:            https://github.com/jub0t/concat
Source0:        https://github.com/jub0t/concat/releases/download/v0.2.8/Concat-0.2.8-linux-x86_64.rpm
BuildRequires:  cpio
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
Requires:       Mesa-libGL1
Requires:       fontconfig
Requires:       gtk3
Requires:       hicolor-icon-theme
Requires:       libasound2
Requires:       libfreetype6
Requires:       libgcc_s1
Requires:       libstdc++6
Requires:       libxkbcommon-x11-0
Requires:       libxkbcommon0
Recommends:     xdg-desktop-portal
Recommends:     xdg-desktop-portal-gtk
ExclusiveArch:  x86_64

%description
Concat is a free and open source cross-platform video editor (timeline
editing, effects, transitions, titles, captions and speech) with FFmpeg
underneath and hardware-accelerated preview and export.

%prep
%setup -q -c -T
rpm2cpio %{SOURCE0} | cpio -idmv

%build

%install
install -d -m 0755 %{buildroot}/opt/concat
cp -a opt/concat/* %{buildroot}/opt/concat/

chmod 755 %{buildroot}/opt/concat/lib/*.so*

install -d -m 0755 %{buildroot}%{_bindir}
install -m 0755 usr/bin/concat %{buildroot}%{_bindir}/concat

install -d -m 0755 %{buildroot}%{_datadir}
cp -a usr/share/applications %{buildroot}%{_datadir}/
cp -a usr/share/icons %{buildroot}%{_datadir}/
cp -a usr/share/doc %{buildroot}%{_datadir}/

sed -i 's|^Exec=.*|Exec=%{_bindir}/concat %U|' \
    %{buildroot}%{_datadir}/applications/concat.desktop

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/concat.desktop

%files
%license %{_datadir}/doc/concat/LICENSE
%dir %{_datadir}/doc/concat
%doc %{_datadir}/doc/concat/THIRD_PARTY_NOTICES.md
%{_bindir}/concat
%{_datadir}/applications/concat.desktop
%{_datadir}/icons/hicolor/256x256/apps/concat.png
/opt/concat/

%changelog
