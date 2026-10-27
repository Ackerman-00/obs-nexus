%global debug_package %{nil}
%global __os_install_post %{nil}
%global __requires_exclude_from ^/opt/rootapp/.*$
%global __provides_exclude_from ^/opt/rootapp/.*$
Name:           rootapp
Version:        0.9.155
Release:        0
Summary:        Discord alternative for gaming communities and large groups
License:        SUSE-Freeware
URL:            https://www.rootapp.com
Source0:        https://installer.rootapp.com/installer/Linux/X64/Root.AppImage
BuildRequires:  binutils
BuildRequires:  hicolor-icon-theme
BuildRequires:  squashfs
# Runtime set re-derived from the payload itself (2026-10-27 full teardown of
# the pinned Root.AppImage: sha256 matches, 483 files, 18 ELFs, ASCII + UTF-16
# string scans of every file - UTF-16 matters because `Root` is a .NET binary
# and its DllImport probe table is stored that way). auto-Requires are off for
# the /opt payload (__requires_exclude_from above), so every runtime library
# has to be written out here:
#
#   (1) DT_NEEDED union of every shipped ELF (readelf -d). Excluded: glibc
#       (libc/libm/libpthread/libdl/librt/ld-linux - always present) and
#       libjawt, which only the bundled JRE's libawt_toolkit.so needs, not the
#       OS.
#   (2) + the libraries the payload loads BY NAME at runtime: Chromium's
#       dlopen list and `Root`'s .NET probe table - libwayland-client (the app
#       is Avalonia with a native Wayland backend now: assembly
#       Avalonia.Wayland + dlopen of libwayland-client.so.0), GL/EGL/Vulkan,
#       Pulse + PipeWire (LiveKit voice/video, screen-cast audio), the X11
#       extras (uiohook hotkeys, cursor, screensaver inhibit, input), OpenSSL
#       and Kerberos (.NET TLS / SPNEGO), VA-API (LiveKit video decode).
#
# Deliberately NOT required, each verified against this payload rather than
# assumed: wl-clipboard - zero references anywhere, ASCII or UTF-16, the
# clipboard is in-process (X11 selection / Wayland protocol), no helper is
# ever exec'd; libvlc - LibVLCSharp P/Invoke declarations only; speechd,
# GTK4, CUDA/NVIDIA/onnxruntime providers, librenderdoc - optional probes
# that degrade to a fallback; xdg-desktop-portal - any session able to run
# this on Wayland already ships it.
Requires:       at-spi2-core
Requires:       hicolor-icon-theme
Requires:       mozilla-nspr
Requires:       mozilla-nss
Requires:       xdg-utils
# --- sonames: DT_NEEDED union (see above) -------------------------------
Requires:       libX11.so.6()(64bit)
Requires:       libXcomposite.so.1()(64bit)
Requires:       libXdamage.so.1()(64bit)
Requires:       libXext.so.6()(64bit)
Requires:       libXfixes.so.3()(64bit)
Requires:       libXinerama.so.1()(64bit)
Requires:       libXrandr.so.2()(64bit)
Requires:       libXt.so.6()(64bit)
Requires:       libXtst.so.6()(64bit)
Requires:       libasound.so.2()(64bit)
Requires:       libatk-1.0.so.0()(64bit)
Requires:       libatk-bridge-2.0.so.0()(64bit)
Requires:       libatspi.so.0()(64bit)
Requires:       libcairo.so.2()(64bit)
Requires:       libcups.so.2()(64bit)
Requires:       libdbus-1.so.3()(64bit)
Requires:       libexpat.so.1()(64bit)
Requires:       libfontconfig.so.1()(64bit)
Requires:       libgbm.so.1()(64bit)
Requires:       libgcc_s.so.1()(64bit)
Requires:       libgdk-3.so.0()(64bit)
Requires:       libgio-2.0.so.0()(64bit)
Requires:       libglib-2.0.so.0()(64bit)
Requires:       libgobject-2.0.so.0()(64bit)
Requires:       libgtk-3.so.0()(64bit)
Requires:       libpango-1.0.so.0()(64bit)
Requires:       libstdc++.so.6()(64bit)
Requires:       libudev.so.1()(64bit)
Requires:       libxcb.so.1()(64bit)
Requires:       libxkbcommon.so.0()(64bit)
# --- sonames: loaded by name at runtime (dlopen / .NET probe table) -----
Requires:       libEGL.so.1()(64bit)
Requires:       libGL.so.1()(64bit)
Requires:       libICE.so.6()(64bit)
Requires:       libSM.so.6()(64bit)
Requires:       libX11-xcb.so.1()(64bit)
Requires:       libXcursor.so.1()(64bit)
Requires:       libXi.so.6()(64bit)
Requires:       libXss.so.1()(64bit)
Requires:       libgssapi_krb5.so.2()(64bit)
Requires:       libpipewire-0.3.so.0()(64bit)
Requires:       libpulse.so.0()(64bit)
Requires:       libssl.so.3()(64bit)
Requires:       libva-drm.so.2()(64bit)
Requires:       libva.so.2()(64bit)
Requires:       libvulkan.so.1()(64bit)
Requires:       libwayland-client.so.0()(64bit)
Provides:       rootapp = %{version}-%{release}
# sha256: 306824e30d41334a7fa569b5d7e08837e5d0e7110b48eb214c987bfe2fea34a1
ExclusiveArch:  x86_64

%description
Root App is a new Discord alternative, designed for gaming communities and
large online groups.

%prep
%setup -q -c -T

OFFSET=$(LC_ALL=C readelf -h %{SOURCE0} | awk 'NR==13{e_shoff=$5} NR==18{e_shentsize=$5} NR==19{e_shnum=$5} END{print e_shoff+e_shentsize*e_shnum}')
unsquashfs -q -d squashfs-root -o "$OFFSET" %{SOURCE0}
chmod go-w squashfs-root

%build

%install
install -dm755 %{buildroot}/opt/rootapp
cp -ar squashfs-root/* %{buildroot}/opt/rootapp/

# Root.dbg is the split debug companion of usr/bin/Root: same GNU build-id
# (d66170ab62b2f9a92ae918223266c3c6195fbd53), referenced only by Root's own
# .gnu_debuglink section - pure DWARF, never loaded at runtime. It is 352 MB
# of a 1.4 GB payload, and this package sets debug_package %{nil}, so it would
# ship to /opt with no debugger story attached. Drop it.
rm -f %{buildroot}/opt/rootapp/usr/bin/Root.dbg

# No chrome-sandbox handling: the payload ships no sandbox helper at all
# (0.9.155 teardown finds zero files matching *sandbox*), so the old setuid
# block was dead code. Do not reintroduce a 4755 bit on /opt without an
# upstream file to put it on.

install -dm755 %{buildroot}%{_bindir}
cat > %{buildroot}%{_bindir}/rootapp <<'WRAPPER_EOF'
#!/bin/sh
export APPDIR="/opt/rootapp"
exec /opt/rootapp/AppRun "$@"
WRAPPER_EOF
chmod 755 %{buildroot}%{_bindir}/rootapp

# Upstream Root.png is 512x512 (verified by IHDR, 2026-10-27): install it
# into the matching hicolor size class, not 256x256 as before.
install -Dm644 squashfs-root/Root.png %{buildroot}%{_datadir}/pixmaps/rootapp.png
install -Dm644 squashfs-root/Root.png %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/rootapp.png

install -dm755 %{buildroot}%{_datadir}/applications/
cat > %{buildroot}%{_datadir}/applications/rootapp.desktop <<DESKTOP_EOF
[Desktop Entry]
Type=Application
Name=Root
Comment=Root App is a new Discord alternative, designed for gaming communities and large online groups
Exec=rootapp %U
Icon=rootapp
Terminal=false
StartupWMClass=Root
Categories=Network;InstantMessaging;
MimeType=x-scheme-handler/rootapp;
DESKTOP_EOF

%files
%{_bindir}/rootapp
/opt/rootapp/
%{_datadir}/applications/rootapp.desktop
%{_datadir}/icons/hicolor/*/apps/rootapp.png
%{_datadir}/pixmaps/rootapp.png

%changelog
