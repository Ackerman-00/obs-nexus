Format: 3.0 (quilt)
Source: obsidian
Binary: obsidian
Architecture: any
Version: 1.14.4
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), desktop-file-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is a plain (uncompressed) wrapper tar holding BOTH upstream
# AppImages (x86_64 + arm64); debian/rules picks per DEB_HOST_ARCH. The wrapper
# is versioned per bump and maintained by update.sh alongside the spec.
Debtransform-Tar: obsidian-1.14.4.tar
