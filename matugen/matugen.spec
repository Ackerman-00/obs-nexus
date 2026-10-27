Name:           matugen
Version:        4.2.0
Release:        0
Summary:        Material You color generation tool (Nexus Optimized)
License:        GPL-2.0-or-later AND MIT AND Apache-2.0 AND Zlib
Group:          System/GUI/Other
URL:            https://github.com/InioX/matugen
Source0:        %{name}-%{version}.tar.gz
Source1:        vendor.tar.xz
Source2:        cargo_config
BuildRequires:  cargo
BuildRequires:  cargo-packaging
BuildRequires:  gcc-c++
ExclusiveArch:  x86_64

%description
Matugen is a Material You color generation tool that supports templates.
Packaged exclusively for the Nexus repository. This version is compiled natively from the official Rust crate for peak performance in Wayland environments.

%prep
%autosetup -p1 -a1
mkdir -p .cargo
cp %{SOURCE2} .cargo/config

%build
%{cargo_build}

%install
%{cargo_install}

%files
%license LICENSE
%{_bindir}/matugen

%changelog
