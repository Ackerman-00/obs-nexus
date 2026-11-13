%global debug_package %{nil}

Name:           whitesur-icon-theme
Version:        2026.09.10
Release:        0
Summary:        WhiteSur macOS-like icon theme
License:        GPL-3.0-or-later
Group:          System/GUI/Other
URL:            https://github.com/vinceliuice/WhiteSur-icon-theme
Source0:        https://github.com/vinceliuice/WhiteSur-icon-theme/archive/refs/tags/2026-09-10.tar.gz
# sha256:  406c9cd59705583f1754b0eaca96cc48bafda042b88ef143f16d8ae1820ecd95
BuildArch:      noarch
BuildRequires:  bash
BuildRequires:  coreutils
BuildRequires:  gtk3-tools
BuildRequires:  sed
ExclusiveArch:  x86_64
Requires:       hicolor-icon-theme

%description
WhiteSur is a macOS-like icon theme for Linux desktops. This package ships the
upstream 2026-09-10 release with every color variant (default, light and dark
for the base theme plus the purple, pink, red, orange, yellow, green, grey
and nord color themes).

%prep
%setup -q -n WhiteSur-icon-theme-2026-09-10

%build

%install
install -d -m 0755 %{buildroot}%{_datadir}/icons
bash ./install.sh --dest %{buildroot}%{_datadir}/icons --theme all

for t in %{buildroot}%{_datadir}/icons/WhiteSur*; do
    gtk-update-icon-cache -q "$t" 2>/dev/null || true
done

%files
%license COPYING
%{_datadir}/icons/WhiteSur*

%post
gtk-update-icon-cache -q %{_datadir}/icons/WhiteSur 2>/dev/null || :
for t in %{_datadir}/icons/WhiteSur*; do gtk-update-icon-cache -q "$t" 2>/dev/null || :; done

%postun
gtk-update-icon-cache -q %{_datadir}/icons/WhiteSur 2>/dev/null || :
for t in %{_datadir}/icons/WhiteSur*; do gtk-update-icon-cache -q "$t" 2>/dev/null || :; done

%changelog
