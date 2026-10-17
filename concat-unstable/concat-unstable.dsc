Format: 3.0 (quilt)
Source: concat-unstable
Binary: concat-unstable
Architecture: amd64
Version: 0.2.7+git20261017232359.e1009cd
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13), cargo, rustc, gcc, g++, cmake, make, pkgconf, libclang-dev, libfontconfig1-dev, libfreetype6-dev, libxkbcommon-dev, libgl1-mesa-dev, libgtk-3-dev, libasound2-dev, libssl-dev, desktop-file-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the +<build> Debian revision (Version here carries no revision;
# DEBTRANSFORM-RELEASE below adds the autoincremented build counter).
# Debtransform-Tar is the unified snapshot tarball update.sh assembles
# (upstream main tree + vendored crates + BtbN FFmpeg + ONNX libs); all
# build inputs travel in this ONE tarball, so the Debian and RPM builds
# consume identical sources. Version mirrors the spec template.
# OBS appends an autoincremented build number to the DEB version
# (DEBTRANSFORM-RELEASE: 1). Without it every rebuild reuses the SAME
# filename - mangowm_0.18.0-1_amd64.deb - and openSUSE's mirror/CDN
# caches serve the first build's bytes forever, so apt fails with
# 'File has unexpected size' against a stale mirror (MirrorCache
# issue #600). Unique filenames per build fix it permanently.
DEBTRANSFORM-RELEASE: 1
Debtransform-Tar: concat-unstable-0.2.7+git20261017232359.e1009cd.tar.gz
