Format: 3.0 (quilt)
Source: concat
Binary: concat
Architecture: amd64
Version: 0.2.6
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), binutils, xz-utils, zstd, desktop-file-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a plain (uncompressed) wrapper tar holding the upstream
# .deb; it is versioned per bump and maintained by update.sh alongside the
# spec. debian/rules opens it with binutils ar + tar.
Debtransform-Tar: concat-0.2.6.tar
