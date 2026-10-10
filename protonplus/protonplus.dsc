Format: 3.0 (quilt)
Source: protonplus
Binary: protonplus
Architecture: any
Version: 0.6.8
Maintainer: Ackerman-00
Build-Depends: debhelper-compat (= 13), meson, ninja-build, valac, gettext, cmake, pkgconf, appstream, desktop-file-utils, libappstream-dev, libcairo2-dev, libgee-0.8-dev, libglib2.0-dev, libgtk-4-dev, libjson-glib-dev, libadwaita-1-dev (>= 1.6), libarchive-dev, libnotify-dev, libsoup-3.0-dev, libsdl3-dev (>= 3.2.0)
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is the upstream source archive itself (downloaded by
# update.sh); it is versioned per bump. Build-Depends mirror the spec's
# pkgconfig() set 1:1 (libsoup-3.0 is mandatory upstream, not optional).
Debtransform-Tar: protonplus-0.6.8.tar.gz
