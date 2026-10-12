Format: 3.0 (quilt)
Source: matugen
Binary: matugen
Architecture: amd64
Version: 4.2.0
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13), cargo, rustc
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the +<build> Debian revision (Version here carries no revision;
# DEBTRANSFORM-RELEASE below adds the autoincremented build counter).
# Debtransform-Tar is the COMBINED orig tarball update.sh assembles
# (upstream source + vendor/ + cargo_config under one top dir): vendor/
# rides inside the orig tarball so dpkg-source never diffs it. (A previous
# revision merged vendor.tar.xz via Debtransform-Files-Tar, whose merge
# silently dropped every vendor/*/Cargo.toml.orig and broke cargo --
# 2026-10-09. Never reintroduce Files-Tar/Files for vendor content.)
# OBS appends an autoincremented build number to the DEB version
# (DEBTRANSFORM-RELEASE: 1). Without it every rebuild reuses the SAME
# filename - mangowm_0.18.0-1_amd64.deb - and openSUSE's mirror/CDN
# caches serve the first build's bytes forever, so apt fails with
# 'File has unexpected size' against a stale mirror (MirrorCache
# issue #600). Unique filenames per build fix it permanently.
DEBTRANSFORM-RELEASE: 1
Debtransform-Tar: matugen-4.2.0-debian.tar.gz
