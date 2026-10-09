Format: 3.0 (quilt)
Source: openchamber
Binary: openchamber
Architecture: amd64
Version: 2.2.0
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), desktop-file-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a gzip-compressed wrapper tar holding the upstream
# AppImage (dpkg-source 3.0 (quilt) rejects an uncompressed .orig.tar);
# it is versioned per bump and maintained by update.sh alongside
# the spec.
Debtransform-Tar: openchamber-2.2.0.tar.gz
