Format: 3.0 (quilt)
Source: faugus-launcher
Binary: faugus-launcher
Architecture: all
Version: 2.5.1
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13), meson, ninja-build, python3, dh-python, gettext, desktop-file-utils, appstream, libgtk-4-bin
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the +<build> Debian revision (Version here carries no revision;
# DEBTRANSFORM-RELEASE below adds the autoincremented build counter).
# Debtransform-Tar is the upstream source archive itself (downloaded by
# update.sh); it is versioned per bump. Build-Depends mirror the spec's
# build set (meson/ninja/python3/gettext for the msgfmt translation step).
# OBS appends an autoincremented build number to the DEB version
# (DEBTRANSFORM-RELEASE: 1). Without it every rebuild reuses the SAME
# filename and openSUSE's mirror/CDN caches serve the first build's bytes
# forever, so apt fails with 'File has unexpected size' against a stale
# mirror (MirrorCache issue #600). Unique filenames per build fix it.
DEBTRANSFORM-RELEASE: 1
Debtransform-Tar: faugus-launcher-2.5.1.tar.gz
