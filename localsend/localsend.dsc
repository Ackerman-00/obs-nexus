Format: 3.0 (quilt)
Source: localsend
Binary: localsend
Architecture: amd64
Version: 1.18.2
Maintainer: Ackerman-00
Build-Depends: debhelper-compat (= 13), binutils, xz-utils, zstd
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a gzip-compressed wrapper tar holding the upstream
# .deb (dpkg-source 3.0 (quilt) rejects an uncompressed .orig.tar); it is
# versioned per bump and maintained by update.sh alongside the spec.
# debian/rules opens it with binutils ar + tar (same as the RPM %prep).
Debtransform-Tar: localsend-1.18.2.tar.gz
