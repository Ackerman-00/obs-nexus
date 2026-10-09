Format: 3.0 (quilt)
Source: bibata-cursor-theme
Binary: bibata-cursor-theme
Architecture: all
Version: 2.0.7
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), fdupes
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is the upstream release tarball itself (renamed by
# update.sh); it is versioned per bump. Data-only theme, no compilation.
Debtransform-Tar: bibata-cursor-theme-2.0.7.tar.xz
