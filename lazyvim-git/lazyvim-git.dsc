Format: 3.0 (quilt)
Source: lazyvim-git
Binary: lazyvim-git
Architecture: all
Version: 16.0.1+git20260908200953.9997009
Maintainer: Ackerman-00
Build-Depends: debhelper-compat (= 13)
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files into .debian.tar.gz, computes Files:/Checksums, and
# appends the -1 Debian revision (no Debian revision in Version here).
# Debtransform-Tar is the git-snapshot tarball update.sh already generates
# for the RPM flow (lazyvim-<shortcommit>.tar.gz); no extra download. The
# template Version mirrors the spec and is maintained by update.sh per bump.
Debtransform-Tar: lazyvim-9997009.tar.gz
