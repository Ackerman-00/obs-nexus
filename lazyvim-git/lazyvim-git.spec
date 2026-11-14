%global commit          5c26fac21fd3896024a23f2dbc62b722f9a731db
%global shortcommit     5c26fac
%global gitdate         20261108202129
%global base_version    16.0.2
Name:           lazyvim-git
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        Neovim setup for lazy people (Nexus Optimized Git Snapshot)
License:        Apache-2.0
Group:          Productivity/Text/Editors
URL:            https://github.com/LazyVim/LazyVim
Source0:        lazyvim-%{shortcommit}.tar.gz
BuildArch:      noarch
ExclusiveArch:  x86_64
Requires:       git >= 2.19.0
Requires:       neovim >= 0.11.2
Recommends:     fd
Recommends:     gcc
Recommends:     ripgrep

%description
LazyVim is a Neovim setup powered by lazy.nvim to make it easy to
customize and extend your configuration. Packaged exclusively for the
Nexus repository via automated main-branch tracking.

%prep
%autosetup -n LazyVim-%{commit}

%build

%install
install -d -m 0755 %{buildroot}%{_datadir}/lazyvim
cp -a init.lua lua doc queries scripts LICENSE NEWS.md %{buildroot}%{_datadir}/lazyvim/
find %{buildroot} \( -path '*/resources/app-update.yml' -o -path '*/resources/package-type' \) -delete 2>/dev/null || true

%files
%license LICENSE
%doc README.md
%{_datadir}/lazyvim/

%changelog
