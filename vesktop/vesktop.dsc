Format: 3.0 (quilt)
Source: vesktop
Binary: vesktop
Architecture: amd64
Version: 1.6.7
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), python3
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a plain (uncompressed) wrapper tar holding the upstream
# .rpm; it is versioned per bump and maintained by update.sh alongside the
# spec. debian/rpm2tree.py (stdlib-only) materializes the payload at build
# time, so no rpm tooling is needed in the buildroot.
Debtransform-Tar: vesktop-1.6.7.tar
