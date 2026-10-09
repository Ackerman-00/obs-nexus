Format: 3.0 (quilt)
Source: opencode-desktop
Binary: opencode-desktop
Architecture: amd64
Version: 2.0.26
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), binutils, xz-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a gzip-compressed wrapper tar holding the upstream
# .deb (dpkg-source 3.0 (quilt) rejects an uncompressed .orig.tar); it is versioned per bump and maintained by update.sh alongside the
# spec. debian/rules opens it with binutils ar + tar (same as the RPM %prep).
Debtransform-Tar: opencode-desktop-2.0.26.tar.gz
