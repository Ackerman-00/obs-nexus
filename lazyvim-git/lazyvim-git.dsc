Format: 3.0 (quilt)
Source: lazyvim-git
Binary: lazyvim-git
Architecture: all
Version: 16.0.1+git20261028082036.301a3f7
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13)
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (no Debian revision in Version here).
# Debtransform-Tar is the git-snapshot tarball update.sh already generates
# for the RPM flow (lazyvim-<shortcommit>.tar.gz); no extra download. The
# template Version mirrors the spec and is maintained by update.sh per bump.
# OBS appends an autoincremented build number to the DEB version
# (DEBTRANSFORM-RELEASE: 1). Without it every rebuild reuses the SAME
# filename - mangowm_0.18.0-1_amd64.deb - and openSUSE's mirror/CDN
# caches serve the first build's bytes forever, so apt fails with
# 'File has unexpected size' against a stale mirror (MirrorCache
# issue #600). Unique filenames per build fix it permanently.
DEBTRANSFORM-RELEASE: 1
Debtransform-Tar: lazyvim-301a3f7.tar.gz
