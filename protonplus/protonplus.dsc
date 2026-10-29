Format: 3.0 (quilt)
Source: protonplus
Binary: protonplus
Architecture: amd64
Version: 0.6.8
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13), meson, ninja-build, valac, gettext, cmake, pkgconf, python3, appstream, desktop-file-utils, libappstream-dev, libcairo2-dev, libgee-0.8-dev, libglib2.0-dev, libgtk-4-dev, libjson-glib-dev, libadwaita-1-dev (>= 1.6), libarchive-dev, libnotify-dev, libsoup-3.0-dev, libsdl3-dev (>= 3.2.0)
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the +<build> Debian revision (Version here carries no revision;
# DEBTRANSFORM-RELEASE below adds the autoincremented build counter).
# Debtransform-Tar is the upstream source archive itself (downloaded by
# update.sh); it is versioned per bump. Build-Depends mirror the spec's
# pkgconfig() set 1:1 (libsoup-3.0 is mandatory upstream, not optional).
# OBS appends an autoincremented build number to the DEB version
# (DEBTRANSFORM-RELEASE: 1). Without it every rebuild reuses the SAME
# filename - mangowm_0.18.0-1_amd64.deb - and openSUSE's mirror/CDN
# caches serve the first build's bytes forever, so apt fails with
# 'File has unexpected size' against a stale mirror (MirrorCache
# issue #600). Unique filenames per build fix it permanently.
DEBTRANSFORM-RELEASE: 1
Debtransform-Tar: protonplus-0.6.8.tar.gz
