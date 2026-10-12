Format: 3.0 (quilt)
Source: obsidian
Binary: obsidian
Architecture: amd64
Version: 1.14.4
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13), desktop-file-utils, zlib1g, zlib1g-dev
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the +<build> Debian revision (Version here carries no revision;
# DEBTRANSFORM-RELEASE below adds the autoincremented build counter).
# Debtransform-Tar is a gzip-compressed wrapper tar holding the upstream
# AppImage (x86_64; dpkg-source 3.0 (quilt) rejects an uncompressed
# .orig.tar). The wrapper
# is versioned per bump and maintained by update.sh alongside the spec.
# OBS appends an autoincremented build number to the DEB version
# (DEBTRANSFORM-RELEASE: 1). Without it every rebuild reuses the SAME
# filename - mangowm_0.18.0-1_amd64.deb - and openSUSE's mirror/CDN
# caches serve the first build's bytes forever, so apt fails with
# 'File has unexpected size' against a stale mirror (MirrorCache
# issue #600). Unique filenames per build fix it permanently.
DEBTRANSFORM-RELEASE: 1
Debtransform-Tar: obsidian-1.14.4.tar.gz
