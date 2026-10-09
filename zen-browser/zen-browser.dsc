Format: 3.0 (quilt)
Source: zen-browser
Binary: zen-browser
Architecture: amd64
Version: 1.23.2b
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), chrpath, desktop-file-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (Version here carries no revision).
# Debtransform-Tar is the upstream release tarball itself (renamed by
# update.sh); it is versioned per bump. Static branding (wrapper/desktop/
# policies) rides as debian.* copies.
Debtransform-Tar: zen-browser-1.23.2b.tar.xz
