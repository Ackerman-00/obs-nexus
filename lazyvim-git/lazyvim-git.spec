%global commit          301a3f71007c4aa5da5dab82f1a7a08389091224
%global shortcommit     301a3f7
%global gitdate         20261028082036
%global base_version    16.0.1
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
Recommends:     gcc

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

%files
%license LICENSE
%doc README.md
%{_datadir}/lazyvim/

%changelog
