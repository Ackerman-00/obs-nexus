Format: 3.0 (quilt)
Source: rootapp
Binary: rootapp
Architecture: amd64
Version: 0.9.147
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13)
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a gzip-compressed wrapper tar holding the upstream
# AppImage (dpkg-source 3.0 (quilt) rejects an uncompressed .orig.tar); it is versioned per bump and maintained by update.sh alongside
# the spec (the installer URL carries no version - the spec pins sha256).
Debtransform-Tar: rootapp-0.9.147.tar.gz
