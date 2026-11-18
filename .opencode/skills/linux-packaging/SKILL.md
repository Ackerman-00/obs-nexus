---
name: linux-packaging
description: openSUSE RPM and Debian packaging rules for obs-nexus; dependency mapping, spec and .dsc structure, lint and release revision.
---

Read the FULL upstream build system before changing BuildRequires or Build-Depends; record the comparison before the edit.

RPM (openSUSE Tumbleweed, researched 2026-11-18):
- spec-cleaner for style; rpmlint on the SRPM has better coverage than on a bare spec and runs automatically in OBS, where it can fail the build. A `<name>-rpmlintrc` with addFilter() is only for proven false positives.
- Use macros for paths, never mix macros with shell variables; plain shell commands beat %__cat-style command macros. Specs need a license header. No %clean section. %install must not chown - set ownership in %files and use %make_install.
- RPATH is forbidden in openSUSE. %fdupes needs BuildRequires: fdupes.
- systemd units go in %{_unitdir} with %service_add_pre/post/del_preun/del_postun; user units in %{_userunitdir}; tmpfiles in %{_tmpfilesdir} with a %ghost runtime path. Avoid Requires(post): systemd; use %{?systemd_ordering} when ordering matters.
- Shared-library policy: the versioned SO package ships only lib*.so.*; .so links, headers and .pc files go in -devel; add BuildRequires: pkgconfig when shipping .pc. Static libs are discouraged; if required, isolate in -devel-static.
- Naming uses dashes, not underscores/pluses/dots; conflicting commands use update-alternatives with a %ghost alternatives path.
- RPM expands macros even inside # comments; use %dnl or %% to suppress (rpm >= 4.15).

DEB (forky / sid, researched 2026-11-18):
- Declare compatibility with the virtual package debhelper-compat (= 13 or 14); a debian/compat file stops working from debhelper 14. Compat 14 is recommended (testing/unstable ship 14.5); v15 is still experimental.
- debian/rules uses the dh sequencer. One override target per command; duplicate override targets emit make warnings. `dh binary --no-act` confirms an override is registered. execute_before_/execute_after_ hooks need debhelper >= 12.8 and compat >= 10.
- In compat 14+, dh_auto_install installs to debian/tmp by default and files are moved with dh_install; the single-binary addon changes that path.
- Run lintian on the built .deb; lintian-brush fixes 80+ common tags. piuparts tests install/upgrade/remove/purge; autopkgtest uses debian/tests; reprotest + diffoscope prove reproducibility (Debian policy 4.15).
- sbuild with the unshare backend is the recommended clean chroot build (Debian buildds use it); host builds can hide missing Build-Depends.

Bump the RPM Release and DEBTRANSFORM-RELEASE plus both changelogs for every recipe change, or OBS never publishes a new binary.

Sources: en.opensuse.org/openSUSE:Specfile_guidelines, Package_Cleaning, Packaging_checks, Systemd_packaging_guidelines, Shared_library_packaging_policy; debian.org/doc/manuals/debmake-doc/ch06, debhelper dh(1) + compat-upgrade-checklist(7), lintian.debian.org tags, Debian policy 4.15 - fetched 2026-11-18.
