Format: 3.0 (quilt)
Source: matugen
Binary: matugen
Architecture: any
Version: 4.2.0
Maintainer: Ackerman-00 <quietcraft@gmail.com>
Build-Depends: debhelper-compat (= 13), cargo, rustc
# OBS debtransform input (NOT a final .dsc): debtransform runs at build time,
# renames Debtransform-Tar to <source>_<upstream-ver>.orig.tar.gz, bundles the
# flat debian.* files plus Debtransform-Files-Tar/Files into .debian.tar.gz,
# computes Files:/Checksums, and appends the -1 Debian revision (Version here
# carries no revision). The vendored crates + cargo source-replacement config
# reuse the exact artifacts update.sh already generates for the RPM offline
# build (vendor.tar.xz + cargo_config), merged into debian.tar at build time.
Debtransform-Tar: matugen-4.2.0.tar.gz
Debtransform-Files-Tar: vendor.tar.xz
Debtransform-Files: cargo_config
