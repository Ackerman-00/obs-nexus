Format: 3.0 (quilt)
Source: mangowm
Binary: mangowm
Architecture: amd64
Version: 0.18.0
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13), meson, ninja-build, pkg-config
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is the COMBINED orig tarball update.sh assembles
# (upstream mango + wlroots + scenefx trees side by side): extra build
# inputs must ride inside the orig tarball so dpkg-source never diffs
# them (matugen pattern - Files-Tar merging drops files).
Debtransform-Tar: mangowm-0.18.0-debian.tar.gz
