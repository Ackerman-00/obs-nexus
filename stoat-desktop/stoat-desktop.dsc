Format: 3.0 (quilt)
Source: stoat-desktop
Binary: stoat-desktop
Architecture: amd64
Version: 1.5.4
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), unzip, desktop-file-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a plain (uncompressed) wrapper tar holding the upstream
# .zip; it is versioned per bump and maintained by update.sh alongside the
# spec. Static branding (desktop/icon/metainfo) rides as debian.* copies.
Debtransform-Tar: stoat-desktop-1.5.4.tar
