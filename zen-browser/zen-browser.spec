Name:           zen-browser
Version:        1.23.4b
Release:        0
%global __provides_exclude_from ^/usr/lib64/zen-browser/.*$
%global __requires_exclude ^lib(gkcodecs|lgpllibs|mozavcodec|mozavutil|mozgtk|mozsandbox|mozsqlite3|mozwayland|clearkey|freeblpriv3|nss3|nssutil3|ssl3|smime3|nspr4|plc4|plds4)\.so.*$
Summary:        Minimal browser focused on privacy and calm browsing
License:        MPL-2.0
URL:            https://github.com/zen-browser/desktop
Source0:        %{url}/releases/download/%{version}/zen.linux-x86_64.tar.xz
Source1:        zen-browser.sh
Source2:        zen-browser.desktop
Source3:        policies.json
BuildRequires:  chrpath
BuildRequires:  coreutils
BuildRequires:  desktop-file-utils
BuildRequires:  execstack
BuildRequires:  fdupes
BuildRequires:  hicolor-icon-theme
BuildRequires:  hunspell
BuildRequires:  hyphen
BuildRequires:  mozilla-nspr
BuildRequires:  mozilla-nss-certs
Requires:       hunspell
Requires:       hyphen
Requires:       mozilla-nss-certs
Recommends:     xdg-desktop-portal
Recommends:     xdg-desktop-portal-gtk
ExclusiveArch:  x86_64

%description
Zen Browser is a free, open-source web browser based on Mozilla Firefox.It emphasizes privacy, customization, and a modern, distraction-free interface.

Key features:
- Vertical tab sidebar with compact mode
- Workspace management for organizing tabs
- Split view for multitasking
- Firefox Sync support
- Privacy-focused with no tracking
- Compatible with Firefox extensions

%prep
%setup -q -n zen

%build

%install
install -d %{buildroot}%{_bindir}
install -d %{buildroot}%{_datadir}/applications
install -d %{buildroot}%{_libdir}/zen-browser

cp -a * %{buildroot}%{_libdir}/zen-browser/
rm -f %{buildroot}%{_libdir}/zen-browser/removed-files

install -m0755 %{_sourcedir}/zen-browser.sh %{buildroot}%{_bindir}/zen-browser

desktop-file-install --dir=%{buildroot}%{_datadir}/applications %{SOURCE2}

for size in 16x16 32x32 48x48 64x64 128x128; do
    install -Dm644 %{buildroot}%{_libdir}/zen-browser/browser/chrome/icons/default/default${size/x*}.png \
        %{buildroot}%{_datadir}/icons/hicolor/${size}/apps/zen-browser.png
done

install -d %{buildroot}%{_libdir}/zen-browser/distribution
install -m644 %{_sourcedir}/policies.json %{buildroot}%{_libdir}/zen-browser/distribution/policies.json

ln -sf %{_datadir}/hunspell %{buildroot}%{_libdir}/zen-browser/dictionaries
ln -sf %{_datadir}/hyphen %{buildroot}%{_libdir}/zen-browser/hyphenation

rm -f %{buildroot}%{_libdir}/zen-browser/libnssckbi.so
ln -sf %{_libdir}/libnssckbi.so %{buildroot}%{_libdir}/zen-browser/libnssckbi.so

if [ -f "%{buildroot}%{_libdir}/zen-browser/libonnxruntime.so" ]; then
    execstack -c %{buildroot}%{_libdir}/zen-browser/libonnxruntime.so
    chrpath -d %{buildroot}%{_libdir}/zen-browser/libonnxruntime.so
fi

%fdupes %{buildroot}%{_libdir}/zen-browser

%check

%files
%{_bindir}/zen-browser
%{_libdir}/zen-browser
%{_datadir}/applications/zen-browser.desktop
%{_datadir}/icons/hicolor/*/apps/zen-browser.png

%changelog
