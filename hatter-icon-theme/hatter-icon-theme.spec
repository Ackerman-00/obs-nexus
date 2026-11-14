%global debug_package %{nil}

Name:           hatter-icon-theme
Version:        4.0
Release:        0
Summary:        Colorful and customizable icon theme for Linux desktops
License:        GPL-3.0-or-later
Group:          System/GUI/Other
URL:            https://github.com/Mibea/Hatter
Source0:        https://github.com/Mibea/Hatter/archive/refs/tags/V4.0.tar.gz
# sha256:  74fae86c677809198497e735fd3a50c4ff192327bec4ce7bbe35c6844cfaf5fa
Source1:        hatter-icon-theme-rpmlintrc
BuildArch:      noarch
BuildRequires:  bash
BuildRequires:  coreutils
BuildRequires:  fdupes
BuildRequires:  findutils
BuildRequires:  gtk3-tools
BuildRequires:  rsync
BuildRequires:  sed
ExclusiveArch:  x86_64
Requires:       hicolor-icon-theme
Requires(post):   gtk3-tools
Requires(postun): gtk3-tools

%description
Hatter is a modern, colorful and customizable icon theme for Linux desktops.
This package ships the upstream V4.0 build: the base Hatter theme plus the
Hatter-kde and Hatter-kde-dark variants and 19 color variants.

%prep
%setup -q -n Hatter-4.0
find . -depth -name '* *' -exec bash -c 'for f; do mv -- "$f" "${f// /-}"; done' _ {} +

%build
echo 2 | bash ./Build-Hatter.sh

%install
install -d -m 0755 %{buildroot}%{_datadir}/icons
shopt -s nullglob
for t in Build/*/; do
    [ -d "$t" ] || continue
    cp -a "$t" "%{buildroot}%{_datadir}/icons/$(basename "$t")"
done
shopt -u nullglob
find %{buildroot}%{_datadir}/icons -xtype l -delete
for t in %{buildroot}%{_datadir}/icons/*/; do
    gtk-update-icon-cache -q "$t" 2>/dev/null || true
done
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
