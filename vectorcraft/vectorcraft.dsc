Format: 3.0 (quilt)
Source: vectorcraft
Binary: vectorcraft
Architecture: amd64
Version: 0.8.0
Maintainer: Ackerman-00
Build-Depends: debhelper-compat (= 13), binutils, xz-utils, zstd, desktop-file-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a gzip-compressed wrapper tar holding the upstream
# .deb; it is versioned per bump and maintained by update.sh alongside the
# spec. debian/rules opens it with binutils ar + tar.
Debtransform-Tar: vectorcraft-0.8.0.tar.gz
