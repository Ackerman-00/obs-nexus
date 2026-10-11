Format: 3.0 (quilt)
Source: mangowm
Binary: mangowm
Architecture: amd64
Version: 0.18.0
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13), meson, ninja-build, pkg-config,
 libwayland-dev, wayland-protocols, libinput-dev, libxkbcommon-dev,
 libdrm-dev, libpcre2-dev, libpixman-1-dev, libcjson-dev,
 libpango1.0-dev, libcairo2-dev, libxcb1-dev, libxcb-icccm4-dev,
 libxcb-randr0-dev, libxcb-composite0-dev, libxcb-xfixes0-dev,
 libxcb-render0-dev, libxcb-shm0-dev, libdisplay-info-dev,
 libliftoff-dev, libseat-dev, libudev-dev, libgbm-dev, libegl-dev,
 libgles-dev
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is the COMBINED orig tarball update.sh assembles
# (upstream mango + wlroots + scenefx trees side by side): extra build
# inputs must ride inside the orig tarball so dpkg-source never diffs
# them (matugen pattern - Files-Tar merging drops files).
Debtransform-Tar: mangowm-0.18.0-debian.tar.gz
