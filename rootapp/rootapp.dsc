Format: 3.0 (quilt)
Source: rootapp
Binary: rootapp
Architecture: amd64
Version: 0.9.153
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13)
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the +<build> Debian revision (Version here carries no revision;
# DEBTRANSFORM-RELEASE below adds the autoincremented build counter).
# Debtransform-Tar is a gzip-compressed wrapper tar holding the upstream
# AppImage (dpkg-source 3.0 (quilt) rejects an uncompressed .orig.tar); it is versioned per bump and maintained by update.sh alongside
# the spec (the installer URL carries no version - the spec pins sha256).
# OBS appends an autoincremented build number to the DEB version
# (DEBTRANSFORM-RELEASE: 1). Without it every rebuild reuses the SAME
# filename - mangowm_0.18.0-1_amd64.deb - and openSUSE's mirror/CDN
# caches serve the first build's bytes forever, so apt fails with
# 'File has unexpected size' against a stale mirror (MirrorCache
# issue #600). Unique filenames per build fix it permanently.
DEBTRANSFORM-RELEASE: 1
Debtransform-Tar: rootapp-0.9.153.tar.gz
