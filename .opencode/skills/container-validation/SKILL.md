---
name: container-validation
description: Clean-environment proof for RPM and DEB: fresh Tumbleweed and Debian containers, install, rpm -V/dpkg -V, ldd and smoke.
---

One fresh container per package per target.
- RPM: registry.opensuse.org/opensuse/tumbleweed:latest, add the home:ackerman repo from the README, `zypper install`, `rpm -V`, `ldd` over entry points, then a smoke that runs a path the package actually ships.
- DEB: debian:testing and debian:sid with the OBS Debian_Testing / Debian_Unstable repos, `apt install`, `dpkg -V`, `ldd`, smoke. This mirrors the OBS build chroots; a host build can hide a missing Build-Depends.
- For a clean DEB *build*, prefer sbuild (unshare backend, the buildd default) over a host dpkg-buildpackage; run lintian on the result and piuparts for install/upgrade/purge.
- Record PASS/FAIL rows in the install-test table. A same-run install PASS next to a FAIL row is a contradiction that fails the run. A smoke naming a file the package does not ship is PROBE-BUG, not a package FAIL.
- The stamp is baked into app.asar at build time, so a payload strip cannot reach it: patch the build source before packaging, then prove the installed app reports external updates.

Sources: Debian debmake ch06/ch09, sbuild(1), OBS user guide 2.3 - fetched 2026-11-18.
