Format: 3.0 (quilt)
Source: helium-browser
Binary: helium-browser
Architecture: amd64
Version: 0.19.2.1
Maintainer: Ackerman-00
Build-Depends: debhelper-compat (= 13), desktop-file-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is the upstream release tarball itself (renamed by
# update.sh); it is versioned per bump. The metainfo sidecar (absent from
# the tarball) rides as a debian.* copy refreshed per bump by update.sh.
Debtransform-Tar: helium-browser-0.19.2.1.tar.xz
