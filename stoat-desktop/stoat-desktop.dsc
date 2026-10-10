Format: 3.0 (quilt)
Source: stoat-desktop
Binary: stoat-desktop
Architecture: amd64
Version: 1.5.4
Maintainer: Ackerman-00
Build-Depends: debhelper-compat (= 13), unzip, desktop-file-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a gzip-compressed wrapper tar holding the upstream
# .zip (dpkg-source 3.0 (quilt) rejects an uncompressed .orig.tar); it is versioned per bump and maintained by update.sh alongside the
# spec. Static branding (desktop/icon/metainfo) rides as debian.* copies.
Debtransform-Tar: stoat-desktop-1.5.4.tar.gz
