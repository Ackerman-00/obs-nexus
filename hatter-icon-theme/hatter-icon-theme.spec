%global debug_package %{nil}

Name:           hatter-icon-theme
Version:        4.2
Release:        1
Summary:        Colorful and customizable icon theme for Linux desktops
License:        GPL-3.0-or-later
Group:          System/GUI/Other
URL:            https://github.com/Mibea/Hatter
Source0:        https://github.com/Mibea/Hatter/archive/refs/tags/V4.2.tar.gz
# sha256:  e82a1a5a8049c0778b454fbb2a746cb344d65ad2f59ad3b715106ea1b7fea095
Source1:        hatter-icon-theme-rpmlintrc
BuildArch:      noarch
BuildRequires:  bash
BuildRequires:  coreutils
BuildRequires:  fdupes
BuildRequires:  findutils
BuildRequires:  rsync
BuildRequires:  sed
ExclusiveArch:  x86_64
Requires:       hicolor-icon-theme
Requires(post):   gtk3-tools
Requires(postun): gtk3-tools

%description
Hatter is a modern, colorful and customizable icon theme for Linux desktops.
This package ships the full upstream V4.2 build: the base Hatter theme, the
nine Hatter color variants and the nine Hatter-Yaru color variants.

%prep
%setup -q -n Hatter-4.2
find . -depth -name '* *' -exec bash -c 'for f; do d=$(dirname -- "$f"); b=$(basename -- "$f"); mv -- "$f" "$d/${b// /-}"; done' _ {} +

%build
mkdir -p %{_builddir}/icon-cache-shim
printf '#!/bin/sh\nexit 0\n' > %{_builddir}/icon-cache-shim/gtk-update-icon-cache
chmod 755 %{_builddir}/icon-cache-shim/gtk-update-icon-cache
PATH="%{_builddir}/icon-cache-shim:$PATH" bash ./build.sh --all --dest dist

%install
install -d -m 0755 %{buildroot}%{_datadir}/icons
cp -a dist/* %{buildroot}%{_datadir}/icons/
find %{buildroot}%{_datadir}/icons -name icon-theme.cache -delete
find %{buildroot}%{_datadir}/icons -xtype l -delete
find %{buildroot}%{_datadir}/icons -name '*.sh' -exec sed -i '1s|^#!/usr/bin/env bash$|#!/usr/bin/bash|' {} +
%fdupes %{buildroot}%{_datadir}/icons
find %{buildroot} \( -path '*/resources/app-update.yml' -o -path '*/resources/package-type' \) -delete 2>/dev/null || true

%files
%license COPYING
%{_datadir}/icons/Hatter*/

%post
for t in %{_datadir}/icons/Hatter*/; do
    gtk-update-icon-cache -q "$t" 2>/dev/null || :
done

%postun
for t in %{_datadir}/icons/Hatter*/; do
    gtk-update-icon-cache -q "$t" 2>/dev/null || :
done

%changelog
