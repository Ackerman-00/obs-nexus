Format: 3.0 (quilt)
Source: fluxer
Binary: fluxer
Architecture: amd64
Version: 2026.1006.171735
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), python3
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a gzip-compressed wrapper tar holding the upstream
# .rpm (dpkg-source 3.0 (quilt) rejects an uncompressed .orig.tar, so the
# wrapper MUST stay compressed); it is versioned per bump and maintained by
# update.sh alongside the spec. debian/rpm2tree.py (stdlib-only) materializes
# the payload at build time, so no rpm tooling is needed in the buildroot.
Debtransform-Tar: fluxer-2026.1006.171735.tar.gz
