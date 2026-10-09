Format: 3.0 (quilt)
Source: concat-unstable
Binary: concat-unstable
Architecture: amd64
Version: 0.2.6+git20261009164842.c260c2d
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), cargo, rustc, gcc, g++, cmake, make, pkgconf, libclang-dev, libfontconfig1-dev, libfreetype6-dev, libxkbcommon-dev, libgl1-mesa-dev, libgtk-3-dev, libasound2-dev, desktop-file-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is the unified snapshot tarball update.sh assembles
# (upstream main tree + vendored crates + BtbN FFmpeg + ONNX libs); all
# build inputs travel in this ONE tarball, so the Debian and RPM builds
# consume identical sources. Version mirrors the spec template.
Debtransform-Tar: concat-unstable-0.2.6+git20261009164842.c260c2d.tar.gz
