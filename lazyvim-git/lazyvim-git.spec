# These will be automatically populated by update.sh
%global commit          999700997f72227187d49d8b92667183dc7fc809
%global shortcommit     9997009
%global gitdate         20260908200953
%global base_version    16.0.1
Name:           lazyvim-git
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        Neovim setup for lazy people (Nexus Optimized Git Snapshot)
License:        Apache-2.0
Group:          Productivity/Text/Editors
URL:            https://github.com/LazyVim/LazyVim
# Generated dynamically by GitHub Actions
Source0:        lazyvim-%{shortcommit}.tar.gz
BuildArch:      noarch
ExclusiveArch:  x86_64
# Hard runtime requirements per upstream README (Requirements section):
# Neovim >= 0.11.2, Git >= 2.19.0 (Nerd Font / C compiler are optional).
Requires:       git >= 2.19.0
Requires:       neovim >= 0.11.2

%description
LazyVim is a Neovim setup powered by lazy.nvim to make it easy to
customize and extend your configuration. Packaged exclusively for the
Nexus repository via automated main-branch tracking.

%prep
%autosetup -n LazyVim-%{commit}

%build
# Pure configuration files, no compilation needed

%install
install -d -m 0755 %{buildroot}%{_datadir}/lazyvim
cp -a init.lua lua doc queries scripts LICENSE NEWS.md %{buildroot}%{_datadir}/lazyvim/

%files
%license LICENSE
%doc README.md
%{_datadir}/lazyvim/

%changelog
