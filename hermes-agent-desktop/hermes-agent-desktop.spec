%global debug_package %{nil}
%global __requires_exclude_from ^/opt/HermesDesktop/.*$
%global __provides_exclude_from ^/opt/HermesDesktop/.*$
%global __brp_mangle_shebangs_exclude_from ^/opt/HermesDesktop/.*$
%global commit          5c1abd257d0cc1b531ffee6e50bef0621aa49dc4
%global shortcommit     5c1abd2
%global gitdate         20261113141540
%global base_version    0.23.1

Name:           hermes-agent-desktop
Version:        %{base_version}+git%{gitdate}.%{shortcommit}
Release:        0
Summary:        Native desktop shell for Hermes Agent (git snapshot)
License:        MIT
Group:          Development/Tools/IDE
URL:            https://github.com/NousResearch/hermes-agent
Source0:        https://github.com/NousResearch/hermes-agent/archive/%{commit}.tar.gz
# sha256:  23c292a2db4218393104864680ae44cbef003c75016c9d456a8fdc3629c6f04d
Source1:        https://nodejs.org/download/release/v26.12.1/node-v26.12.1-linux-x64.tar.xz
# sha256:  23c292a2db4218393104864680ae44cbef003c75016c9d456a8fdc3629c6f04d
Source2:        https://registry.npmjs.org/@pnpm/exe.linux-x64/-/exe.linux-x64-12.15.0.tgz
# sha256:  23c292a2db4218393104864680ae44cbef003c75016c9d456a8fdc3629c6f04d
Source3:        hermes-agent-desktop-rpmlintrc
ExclusiveArch:  x86_64

BuildRequires:  binutils
BuildRequires:  curl
BuildRequires:  desktop-file-utils
BuildRequires:  gcc
BuildRequires:  gcc-c++
BuildRequires:  git
BuildRequires:  libatomic_ops-devel
BuildRequires:  libX11-devel
BuildRequires:  libXi-devel
BuildRequires:  make
BuildRequires:  python3
BuildRequires:  tar
BuildRequires:  xz
BuildRequires:  zstd

Requires:       at-spi2-core
Requires:       hicolor-icon-theme
Requires:       mozilla-nss
Requires:       xdg-utils
Requires:       libasound.so.2()(64bit)
Requires:       libatk-1.0.so.0()(64bit)
Requires:       libatk-bridge-2.0.so.0()(64bit)
Requires:       libatspi.so.0()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libcups.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libdrm.so.2()(64bit)
Requires:       libexpat.so.1()(64bit)
Requires:       libgbm.so.1()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgtk-3.so.0()(64bit)
Requires:       libnspr4.so()(64bit)
Requires:       libnss3.so()(64bit)
Requires:       libnssutil3.so()(64bit)
Requires:       libnotify.so.4()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
Requires:       libpipewire-0.3.so.0()(64bit)
Requires:       libpulse.so.0()(64bit)
Requires:       libsecret-1.so.0()(64bit)
Requires:       libsmime3.so()(64bit)
Requires:       libstdc++.so.6()(64bit)
Requires:       libudev.so.1()(64bit)
Requires:       libXi.so.6()(64bit)
Requires:       libX11.so.6()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libXcomposite.so.1()(64bit)
Requires:       libXdamage.so.1()(64bit)
Requires:       libXext.so.6()(64bit)
Requires:       libXfixes.so.3()(64bit)
Requires:       libXrandr.so.2()(64bit)
Requires:       libXss.so.1()(64bit)
Requires:       libXtst.so.6()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
Requires:       libuuid.so.1()(64bit)
Requires(posttrans): gtk3-tools
Requires(postun): gtk3-tools
Recommends:     ffmpeg

%description
Hermes Agent desktop: chat sessions, background agent work, file browsing and
management, integrated terminal and browser, previews, sessions, memory and
skills. This package is built from the current upstream git snapshot with the
upstream Node 26 and pnpm 12 toolchain.

%prep
%autosetup -n hermes-agent-%{commit}
mkdir -p .tools/node .tools/pnpm
tar -xJf %{SOURCE1} -C .tools/node --strip-components=1
tar -xzf %{SOURCE2} -C .tools/pnpm
export PATH="$PWD/.tools/node/bin:$PWD/.tools/pnpm/package:$PATH"
node --version
pnpm --version

%build
export PATH="$PWD/.tools/node/bin:$PWD/.tools/pnpm/package:$PATH"
if ! curl -fsS --max-time 20 -o /dev/null https://registry.npmjs.org/ ; then
  echo 'ERROR: no outbound network in this build container - pnpm install needs the npm registry' >&2
  exit 1
fi
pnpm install --frozen-lockfile
pnpm --filter hermes run build
node scripts/build/electron-runtime.mjs --source .
cd apps/desktop
node scripts/run-electron-builder.mjs --linux --x64 --dir --publish never
cd ../..

%install
install -d %{buildroot}/opt/HermesDesktop %{buildroot}%{_bindir}
install -Dpm0644 LICENSE %{buildroot}%{_licensedir}/%{name}/LICENSE
if [ -d apps/desktop/release/linux-unpacked ]; then
    cp -a apps/desktop/release/linux-unpacked/* %{buildroot}/opt/HermesDesktop/
else
    echo "ERROR: electron-builder did not produce release/linux-unpacked" >&2
    exit 1
fi
install -Dpm0644 %{buildroot}/opt/HermesDesktop/resources/app.asar.unpacked/dist/hermes.png %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/hermes-agent-desktop.png

cat > %{buildroot}%{_bindir}/hermes-agent-desktop <<'WRAPPER_EOF'
#!/bin/sh
exec /opt/HermesDesktop/Hermes "$@"
WRAPPER_EOF
chmod 755 %{buildroot}%{_bindir}/hermes-agent-desktop

install -d %{buildroot}%{_datadir}/applications
cat > %{buildroot}%{_datadir}/applications/hermes-agent-desktop.desktop <<'DESKTOP_EOF'
[Desktop Entry]
Type=Application
Name=Hermes Agent Desktop
Comment=Native desktop shell for Hermes Agent
Exec=hermes-agent-desktop %U
Terminal=false
Categories=Development;
Icon=hermes-agent-desktop
DESKTOP_EOF

%post
/bin/touch --no-create %{_datadir}/icons/hicolor >/dev/null 2>&1 || :
/usr/bin/gtk-update-icon-cache -q %{_datadir}/icons/hicolor >/dev/null 2>&1 || :

%postun
case "$1" in
    0)
        /bin/touch --no-create %{_datadir}/icons/hicolor >/dev/null 2>&1
        /usr/bin/gtk-update-icon-cache -q %{_datadir}/icons/hicolor >/dev/null 2>&1 || :
        ;;
esac

%posttrans
/usr/bin/gtk-update-icon-cache -q %{_datadir}/icons/hicolor >/dev/null 2>&1 || :

%files
%license %{_licensedir}/%{name}/LICENSE
%{_bindir}/hermes-agent-desktop
%{_datadir}/applications/hermes-agent-desktop.desktop
%{_datadir}/icons/hicolor/512x512/apps/hermes-agent-desktop.png
%dir /opt/HermesDesktop
%exclude /opt/HermesDesktop/chrome-sandbox
/opt/HermesDesktop/
%attr(4755, root, root) /opt/HermesDesktop/chrome-sandbox

%changelog
