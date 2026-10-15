Name:           faugus-launcher
Version:        2.4.4
Release:        0
ExclusiveArch:  x86_64
Summary:        Lightweight app for running Windows games using UMU-Launcher
License:        MIT
Group:          System/GUI/Other
URL:            https://github.com/Faugus/faugus-launcher
Source0:        %{url}/archive/refs/tags/%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  appstream-glib
BuildRequires:  desktop-file-utils
BuildRequires:  fdupes
BuildRequires:  gettext-runtime
BuildRequires:  gtk3-tools
BuildRequires:  meson >= 1.2.0
BuildRequires:  ninja
BuildRequires:  python3-rpm-macros
# Upstream is pure Python + meson (meson.build + py.install_sources);
# byte-compile at install time needs the interpreter only.
BuildRequires:  python3
# Upstream runtime set (packaging/fedora/faugus-launcher.spec Requires +
# README Dependencies): pygobject/requests/pillow/vdf/psutil/dbus-python/
# icoextract/gtk4/libadwaita/libmanette. dbus maps to python3-dbus-python
# on Tumbleweed (python3-dbus is NOT-PROVIDED, proven via OSS primary.xml);
# GI imports need the typelib split packages, not the source names.
Requires:       hicolor-icon-theme
Requires:       python3-gobject
Requires:       python3-requests
Requires:       python3-Pillow
Requires:       python3-vdf
Requires:       python3-psutil
Requires:       python3-dbus-python
Requires:       python3-icoextract
Requires:       typelib-1_0-Gtk-4_0
Requires:       typelib-1_0-Adw-1
Requires:       typelib-1_0-Manette-0_2-0

%description
Faugus is a simple and lightweight app for running Windows games using
UMU-Launcher/UMU-Proton. The umu-run component is downloaded and managed
by the app itself at runtime, so no umu Requires is shipped here.

%package lang
Summary:        Translations for package %{name}
Group:          System/Localization
Requires:       %{name} = %{version}-%{release}
BuildArch:      noarch

%description lang
Provides translations for the "%{name}" package.

%prep
%autosetup -n %{name}-%{version}

%build
%meson --prefix=%{_prefix}
%meson_build

%install
%meson_install
%find_lang faugus-launcher
%fdupes %{buildroot}

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/io.github.Faugus.faugus-launcher.desktop
desktop-file-validate %{buildroot}%{_datadir}/applications/io.github.Faugus.faugus-launcher.shortcut.desktop

%files
%license LICENSE
%{_bindir}/faugus-launcher
%{python3_sitelib}/faugus/
%{_datadir}/faugus-launcher/
%{_datadir}/applications/io.github.Faugus.faugus-launcher.desktop
%{_datadir}/applications/io.github.Faugus.faugus-launcher.shortcut.desktop
%{_datadir}/icons/hicolor/scalable/actions/faugus-*.svg
%{_datadir}/icons/hicolor/scalable/apps/faugus-launcher.svg
%{_datadir}/icons/hicolor/scalable/apps/faugus-mono.svg
%{_datadir}/icons/hicolor/scalable/apps/io.github.Faugus.faugus-launcher.svg
%{_datadir}/metainfo/io.github.Faugus.faugus-launcher.metainfo.xml

%files lang -f faugus-launcher.lang

%changelog
