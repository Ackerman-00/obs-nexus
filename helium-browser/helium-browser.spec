%global             debug_package %{nil}
%global             helium_base /opt/helium
# Prevent RPM from trying to auto-generate dependencies from the bundled Chromium libraries
%global __requires_exclude_from ^/opt/helium/.*$
%global __provides_exclude_from ^/opt/helium/.*$
Name:           helium-browser
Version:        0.19.1.2
Release:        0
Summary:        Private, fast, and honest web browser
License:        GPL-3.0-only
Group:          Productivity/Networking/Web/Browsers
URL:            https://github.com/imputnet/helium-linux
Source0:        https://github.com/imputnet/helium-linux/releases/download/%{version}/helium-%{version}-x86_64_linux.tar.xz
# The official binary tarball does not ship the metainfo file, so pull it
# from the repo at the matching release tag (all release tags carry it).
Source1:        https://raw.githubusercontent.com/imputnet/helium-linux/%{version}/package/net.imput.helium.metainfo.xml
Source2:        helium-browser-rpmlintrc
BuildRequires:  desktop-file-utils
BuildRequires:  hicolor-icon-theme
# Runtime dependencies for the bundled Chromium binary (auto-requires for
# /opt/helium are excluded above, so list them explicitly)
Requires:       libasound.so.2()(64bit)
Requires:       libgbm.so.1()(64bit)
Requires:       libnspr4.so()(64bit)
Requires:       libnss3.so()(64bit)
Requires:       libnssutil3.so()(64bit)
Requires:       libsmime3.so()(64bit)
Requires(post): desktop-file-utils
Requires(posttrans): gtk3-tools
Requires(postun): gtk3-tools
Recommends:     liberation-fonts
Recommends:     vulkan-loader
# www-browser convention shared by openSUSE's firefox/chromium packages
Provides:       www-browser = %{version}-%{release}
ExclusiveArch:  x86_64

%description
Helium is a private, fast, and honest web browser based on Chromium.
It strips Google services, telemetry and other privacy-invasive features,
while keeping the Chromium browsing experience.

%prep
%setup -q -n helium-%{version}-x86_64_linux

%build
# Using prebuilt binaries

%install
mkdir -p %{buildroot}%{helium_base} \
         %{buildroot}%{_bindir} \
         %{buildroot}%{_datadir}/applications \
         %{buildroot}%{_datadir}/metainfo \
         %{buildroot}%{_datadir}/icons/hicolor/256x256/apps

cp -a . %{buildroot}%{helium_base}

# Brand the wrapper so bug reports show the distribution the build came from
sed -Ei "s/(CHROME_VERSION_EXTRA=).*/\1suse/" \
    %{buildroot}%{helium_base}/helium-wrapper

install -m 644 product_logo_256.png \
    %{buildroot}%{_datadir}/icons/hicolor/256x256/apps/helium.png

desktop-file-install --dir=%{buildroot}%{_datadir}/applications \
    %{buildroot}%{helium_base}/helium.desktop

install -m 644 %{SOURCE1} \
    %{buildroot}%{_datadir}/metainfo/net.imput.helium.metainfo.xml

ln -sf %{helium_base}/helium-wrapper %{buildroot}%{_bindir}/helium

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/helium.desktop

%post
# Refresh the desktop database and icon cache
%{_bindir}/update-desktop-database > /dev/null 2>&1 || :
/bin/touch --no-create %{_datadir}/icons/hicolor > /dev/null 2>&1 || :

%postun
%{_bindir}/update-desktop-database > /dev/null 2>&1 || :
case "$1" in
    0)
        /bin/touch --no-create %{_datadir}/icons/hicolor > /dev/null 2>&1
        %{_bindir}/gtk-update-icon-cache %{_datadir}/icons/hicolor > /dev/null 2>&1 || :
        ;;
esac

%posttrans
%{_bindir}/gtk-update-icon-cache %{_datadir}/icons/hicolor > /dev/null 2>&1 || :

%files
%{helium_base}/
%{_bindir}/helium
%{_datadir}/applications/helium.desktop
%{_datadir}/metainfo/net.imput.helium.metainfo.xml
%{_datadir}/icons/hicolor/256x256/apps/helium.png

%changelog
