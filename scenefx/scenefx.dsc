Format: 3.0 (quilt)
Source: scenefx
Binary: scenefx
Architecture: amd64
Version: 0.5
Maintainer: Ackerman-00 <noreply@example.com>
Build-Depends: debhelper-compat (= 13), meson, ninja-build, pkg-config,
 libwayland-dev, libwayland-bin, wayland-protocols (>= 1.41),
 libdrm-dev, libxkbcommon-dev, libpixman-1-dev,
 libwlroots-0.20-dev (>= 0.20),
 libgbm-dev, libegl-dev, libgles-dev, liblcms2-dev
# OBS debtransform input (NOT a final .dsc). Debtransform-Tar is the
# upstream release tarball (content-identical rename, maintained by
# update.sh alongside the spec).
Debtransform-Tar: scenefx-0.5.tar.gz
