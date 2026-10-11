Format: 3.0 (quilt)
Source: mangowm
Binary: mangowm
Architecture: amd64
Version: 0.18.0
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13), meson, ninja-build, pkg-config,
 libwayland-dev, libwayland-bin, wayland-protocols, libinput-dev,
 libxkbcommon-dev, libdrm-dev, libpcre2-dev, libpixman-1-dev,
 libcjson-dev, libpango1.0-dev, libcairo2-dev, libxcb1-dev,
 libxcb-icccm4-dev, libxcb-randr0-dev,
 libwlroots-0.20-dev (>= 0.20), libscenefx-0.5-dev (>= 0.5)
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is the upstream source archive (mango tree only;
# wlroots and scenefx both resolve from the distro (libwlroots-0.20-dev,
# libscenefx-0.5-dev - same SONAMEs and .pc as ours, so shipping our own
# would collide). Tumbleweed has no scenefx at all, so the RPM side still
# builds scenefx from source in this repo. Mirrors debian/control
# Build-Depends.
Debtransform-Tar: mangowm-0.18.0.tar.gz
