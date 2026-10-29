Format: 3.0 (quilt)
Source: helium-browser
Binary: helium-browser
Architecture: amd64
Version: 0.20.2.1
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13), desktop-file-utils
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the +<build> Debian revision (Version here carries no revision;
# DEBTRANSFORM-RELEASE below adds the autoincremented build counter).
# Debtransform-Tar is the upstream release tarball itself (renamed by
# update.sh); it is versioned per bump. The metainfo sidecar (absent from
# the tarball) rides as a debian.* copy refreshed per bump by update.sh.
# OBS appends an autoincremented build number to the DEB version
# (DEBTRANSFORM-RELEASE: 1). Without it every rebuild reuses the SAME
# filename - mangowm_0.18.0-1_amd64.deb - and openSUSE's mirror/CDN
# caches serve the first build's bytes forever, so apt fails with
# 'File has unexpected size' against a stale mirror (MirrorCache
# issue #600). Unique filenames per build fix it permanently.
DEBTRANSFORM-RELEASE: 1
Debtransform-Tar: helium-browser-0.20.2.1.tar.xz
