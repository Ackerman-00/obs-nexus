%global zig_ver        0.15.2
%global common_build_flags --system %{_builddir}/%{name}-%{version}/vendor/zig/p -Doptimize=ReleaseFast -Dcpu=baseline -Dpie=true -Dstrip=false -Dversion-string=%{version} -fsys=freetype -fsys=harfbuzz -fsys=fontconfig -fsys=libpng -fsys=zlib -fsys=oniguruma -fsys=glslang -fsys=spirv-cross -fsys=simdutf -fsys=gtk4-layer-shell -fsys=highway %{?_smp_mflags}
%define site_runtimepath %{_datadir}/vim/site

Name:           ghostty
Version:        1.3.1
Release:        0
Summary:        Cross-platform terminal emulator
License:        MIT AND OFL-1.1
Group:          System/X11/Terminals
URL:            https://github.com/ghostty-org/ghostty
# Official release tarball (preprocessed, fewer build deps)
# minisig key: RWQlAjJC23149WL2sEpT/l0QKy7hMIFhYdQOFy0Z7z7PbneUgvlsnYcV
Source0:        https://release.files.ghostty.org/%{version}/ghostty-%{version}.tar.gz
# Offline Zig dep cache (update.sh, pinned Zig)
Source1:        vendor.tar.zst
Source2:        https://release.files.ghostty.org/%{version}/ghostty-%{version}.tar.gz.minisig
ExclusiveArch:  x86_64
# Debian wrapper orig: src + vendor cache + pinned Zig (no Zig on Debian)
# Factory BuildRequires set + gettext-runtime for msgfmt
BuildRequires:  fdupes
BuildRequires:  gettext-runtime
BuildRequires:  gobject-introspection
BuildRequires:  hicolor-icon-theme
BuildRequires:  pandoc
BuildRequires:  pkgconfig
BuildRequires:  terminfo
BuildRequires:  zstd
BuildRequires:  zig >= %{zig_ver}
BuildRequires:  cmake(glslang)
BuildRequires:  pkgconfig(bash-completion)
BuildRequires:  pkgconfig(bzip2)
BuildRequires:  pkgconfig(cairo)
BuildRequires:  pkgconfig(cairo-gobject)
BuildRequires:  pkgconfig(gdk-pixbuf-2.0)
BuildRequires:  pkgconfig(gio-2.0)
BuildRequires:  pkgconfig(gobject-2.0)
BuildRequires:  pkgconfig(graphene-1.0)
BuildRequires:  pkgconfig(gtk4)
BuildRequires:  pkgconfig(gtk4-layer-shell-0)
BuildRequires:  pkgconfig(harfbuzz)
BuildRequires:  pkgconfig(libadwaita-1)
BuildRequires:  pkgconfig(libhwy)
BuildRequires:  pkgconfig(libpng)
BuildRequires:  pkgconfig(ncurses)
BuildRequires:  pkgconfig(oniguruma)
BuildRequires:  pkgconfig(pango)
BuildRequires:  pkgconfig(pangocairo)
BuildRequires:  pkgconfig(pixman-1)
BuildRequires:  pkgconfig(simdutf)
BuildRequires:  pkgconfig(spirv-cross-c-shared)
BuildRequires:  pkgconfig(systemd)
BuildRequires:  pkgconfig(vulkan)
BuildRequires:  pkgconfig(zlib)
BuildRequires:  python-nautilus-common-files
BuildRequires:  python3-gobject
Requires:       hicolor-icon-theme
# System terminfo (upstream dir removed at install, Factory parity)
Requires:       terminfo

%description
Ghostty is a fast, feature-rich, and cross-platform terminal
emulator that uses platform-native UI and GPU acceleration.

%package lang
Summary:        Translations for package %{name}
Group:          System/Localization
Requires:       %{name} = %{version}-%{release}
BuildArch:      noarch

%description lang
Provides translations for the "%{name}" package.

%prep
%autosetup -p1 -a1

%build
# Offline build via vendored cache
zig build %{common_build_flags}

%install
export DESTDIR=%{buildroot}
zig build %{common_build_flags} --prefix %{_prefix} --prefix-lib-dir %{_libdir}
mv %{buildroot}%{_datadir}/vim/vimfiles \
  %{buildroot}%{site_runtimepath}
rm -rv %{buildroot}%{_datadir}/terminfo/

mv %{buildroot}%{_datadir}/pkgconfig/ %{buildroot}%{_libdir}

%find_lang com.mitchellh.ghostty

%fdupes %{buildroot}%{_datadir}/icons/hicolor
%fdupes %{buildroot}%{_datadir}/%{name}/themes

chmod 0644 \
    %{buildroot}%{_datadir}/kio/servicemenus/com.mitchellh.ghostty.desktop

%files
%license LICENSE src/font/res/OFL.txt
%{_bindir}/ghostty
%{_datadir}/applications/com.mitchellh.ghostty.desktop
%{_mandir}/man1/ghostty.1%{?ext_man}
%{_mandir}/man5/ghostty.5%{?ext_man}
%{_datadir}/icons/hicolor/128x128/apps/com.mitchellh.ghostty.png
%{_datadir}/icons/hicolor/128x128@2/apps/com.mitchellh.ghostty.png
%{_datadir}/icons/hicolor/16x16/apps/com.mitchellh.ghostty.png
%{_datadir}/icons/hicolor/16x16@2/apps/com.mitchellh.ghostty.png
%{_datadir}/icons/hicolor/256x256/apps/com.mitchellh.ghostty.png
%{_datadir}/icons/hicolor/256x256@2/apps/com.mitchellh.ghostty.png
%{_datadir}/icons/hicolor/32x32/apps/com.mitchellh.ghostty.png
%{_datadir}/icons/hicolor/32x32@2/apps/com.mitchellh.ghostty.png
%{_datadir}/icons/hicolor/512x512/apps/com.mitchellh.ghostty.png
%{_datadir}/icons/hicolor/1024x1024/apps/com.mitchellh.ghostty.png
%dir %{_datadir}/icons/hicolor/128x128@2
%dir %{_datadir}/icons/hicolor/128x128@2/apps
%dir %{_datadir}/icons/hicolor/16x16@2
%dir %{_datadir}/icons/hicolor/16x16@2/apps
%dir %{_datadir}/icons/hicolor/256x256@2
%dir %{_datadir}/icons/hicolor/256x256@2/apps
%dir %{_datadir}/icons/hicolor/32x32@2
%dir %{_datadir}/icons/hicolor/32x32@2/apps
%dir %{_datadir}/ghostty
%dir %{_datadir}/ghostty/shell-integration
%{_datadir}/ghostty/shell-integration/bash/
%{_datadir}/ghostty/shell-integration/elvish/
%{_datadir}/ghostty/shell-integration/fish/
%{_datadir}/ghostty/shell-integration/nushell/
%{_datadir}/ghostty/shell-integration/zsh/
%{_datadir}/ghostty/themes/
%dir %{_datadir}/bat
%dir %{_datadir}/bat/syntaxes
%{_datadir}/bat/syntaxes/ghostty.sublime-syntax
%{_userunitdir}/app-com.mitchellh.ghostty.service
%{_datadir}/dbus-1/services/com.mitchellh.ghostty.service
%{_datadir}/metainfo/com.mitchellh.ghostty.metainfo.xml
%dir %{_datadir}/kio
%dir %{_datadir}/kio/servicemenus
%{_datadir}/kio/servicemenus/com.mitchellh.ghostty.desktop
%{_datadir}/bash-completion/completions/ghostty.bash
%dir %{_datadir}/fish
%dir %{_datadir}/fish/vendor_completions.d
%{_datadir}/fish/vendor_completions.d/ghostty.fish
%dir %{_datadir}/zsh
%dir %{_datadir}/zsh/site-functions
%{_datadir}/zsh/site-functions/_ghostty
%{_datadir}/nautilus-python/extensions/ghostty.py
%{_datadir}/nvim/site/ftdetect/ghostty.vim
%{_datadir}/nvim/site/ftplugin/ghostty.vim
%{_datadir}/nvim/site/syntax/ghostty.vim
%{_datadir}/nvim/site/compiler/ghostty.vim
%dir %{_datadir}/nvim
%dir %{_datadir}/nvim/site
%dir %{_datadir}/nvim/site/ftdetect
%dir %{_datadir}/nvim/site/ftplugin
%dir %{_datadir}/nvim/site/compiler
%dir %{_datadir}/nvim/site/syntax
%dir %{_datadir}/vim
%dir %{site_runtimepath}
%dir %{site_runtimepath}/ftdetect
%dir %{site_runtimepath}/ftplugin
%dir %{site_runtimepath}/syntax
%dir %{site_runtimepath}/compiler
%{site_runtimepath}/ftdetect/ghostty.vim
%{site_runtimepath}/ftplugin/ghostty.vim
%{site_runtimepath}/syntax/ghostty.vim
%{site_runtimepath}/compiler/ghostty.vim
%{_libdir}/libghostty-vt.so.*
%{_libdir}/libghostty-vt.so
%{_libdir}/pkgconfig/libghostty-vt.pc
%dir %{_includedir}/ghostty
%{_includedir}/ghostty/*

%files lang -f com.mitchellh.ghostty.lang

%changelog
