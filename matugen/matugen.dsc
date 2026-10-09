Format: 3.0 (quilt)
Source: matugen
Binary: matugen
Architecture: any
Version: 4.2.0
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), cargo, rustc
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is the COMBINED orig tarball update.sh assembles
# (upstream source + vendor/ + cargo_config under one top dir): vendor/
# rides inside the orig tarball so dpkg-source never diffs it. (A previous
# revision merged vendor.tar.xz via Debtransform-Files-Tar, whose merge
# silently dropped every vendor/*/Cargo.toml.orig and broke cargo --
# 2026-10-09. Never reintroduce Files-Tar/Files for vendor content.)
Debtransform-Tar: matugen-4.2.0-debian.tar.gz
