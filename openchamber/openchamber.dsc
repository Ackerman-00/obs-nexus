Format: 3.0 (quilt)
Source: openchamber
Binary: openchamber
Architecture: amd64
Version: 2.2.0
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13)
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a plain (uncompressed) wrapper tar holding the upstream
# AppImage; it is versioned per bump and maintained by update.sh alongside
# the spec.
Debtransform-Tar: openchamber-2.2.0.tar
