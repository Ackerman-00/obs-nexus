# ⚡ Nexus (openSUSE && Debian)

[![OBS](https://img.shields.io/badge/OBS-home:ackerman-73BA25?style=for-the-badge&logo=opensuse)](https://build.opensuse.org/project/show/home:ackerman)
[![Build](https://img.shields.io/badge/build-status-73BA25?style=for-the-badge&logo=opensuse)](https://build.opensuse.org/project/show/home:ackerman)

**Bleeding-edge Wayland packages for openSUSE Tumbleweed / Slowroll / Leap 16.0, Debian 13 Trixie / Forky / Sid, Ubuntu 26.04 LTS and Arch Linux extra**

Curated packages optimized for minimal Wayland packages. Recipes live in [obs-nexus](https://github.com/Ackerman-00/obs-nexus) and are built on the [openSUSE Build Service](https://build.opensuse.org/project/show/home:ackerman).

> [!NOTE]
> All targets: `.rpm`, `.deb` and Arch packages are published on the
> [OBS project page](https://build.opensuse.org/project/show/home:ackerman).
> That page is the single source of truth for repository URLs and
> add-repo instructions (one per target) - do not copy them from anywhere
> else.

**[browse all packages and their builds online](https://build.opensuse.org/project/show/home:ackerman)**.

---

## Installation

### openSUSE Tumbleweed

```sh
sudo zypper addrepo --refresh \
  https://download.opensuse.org/repositories/home:ackerman/openSUSE_Tumbleweed/home:ackerman.repo
sudo zypper refresh
sudo zypper install <package>
```

The base distribution packages come from the standard Tumbleweed OSS
repository (`https://download.opensuse.org/tumbleweed/repo/oss/`).

### Debian Testing / Unstable

`.deb` builds are published on the
[OBS project page](https://build.opensuse.org/project/show/home:ackerman);
follow the "Download package" instructions there for your release.

## Supported targets

One source tree builds for eight targets on OBS:

| Family | Targets | Recipe |
|---|---|---|
| RPM (zypper) | openSUSE Tumbleweed, Slowroll, Leap 16.0 | `*.spec` |
| DEB (apt) | Debian 13 Trixie, Debian Testing (Forky), Debian Unstable (Sid), Ubuntu 26.04 LTS (Resolute Raccoon) | `<pkg>.dsc` + flat `debian.*` + orig tarball - ONE recipe builds all four |
| Arch (pacman) | Arch Linux `[extra]`, x86_64 | `PKGBUILD` |

---

## Packages

| Package | Description |
|---|---|
| **bibata-cursor-theme** | Open source, compact, material designed cursor set
| **artcraft-launcher** | App launcher for the Craft suite
| **cadcraft** | CAD/drafting - clean-room AutoCAD-style app in pure Rust
| **concat** | Free and open source video editor
| **concat-unstable** | Video editor main-branch snapshot (native source build)
| **designcraft** | Page layout/publishing - clean-room InDesign in pure Rust
| **effectcraft** | Motion graphics/VFX - clean-room After Effects in pure Rust
| **filmcraft** | Video editor - clean-room Premiere Pro in pure Rust
| **fluxer** | Free and open source messaging & VoIP platform
| **helium-browser** | Private, fast, and honest Chromium-based browser
| **localsend** | Open source cross-platform alternative to AirDrop
| **lazyvim-git** | Neovim setup for lazy people (rolling git snapshot)
| **lightcraft** | Photo manager - clean-room Lightroom in pure Rust
| **matugen** | Material You color generation tool
| **obsidian** | Knowledge base for plain-text Markdown notes
| **openchamber** | Agentic development environment boards for issues and pull requests
| **opencode-desktop** | Open source AI coding agent
| **pdfcraft** | Document viewer/editor - clean-room Acrobat in pure Rust
| **photocraft** | Photo editor - clean-room Photoshop in pure Rust
| **protonplus** | Wine and Proton-based compatibility tools manager
| **rootapp** | Discord alternative for gaming communities and large groups
| **soundcraft** | Digital audio workstation - clean-room Pro Tools in pure Rust
| **stoat-desktop** | Open source, user-first chat platform desktop client
| **vectorcraft** | Vector editor - clean-room Illustrator in pure Rust
| **vesktop** | Custom Discord client with Vencord preinstalled
| **zen-browser** | Minimal browser focused on privacy and calm browsing

---

## Build status

Automated OBS builds are triggered by the `update-packages.yml` pipeline (runs every 6h) which syncs changed packages to OBS and rebuilds them, and the autonomous opencode maintainer verifies and repairs failed builds on the same schedule.

| Project | Status |
|---|---|
| `home:ackerman` | [View builds](https://build.opensuse.org/project/show/home:ackerman) |
