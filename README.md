# ⚡ Nexus (openSUSE && Debian)

[![OBS](https://img.shields.io/badge/OBS-home:ackerman-73BA25?style=for-the-badge&logo=opensuse)](https://build.opensuse.org/project/show/home:ackerman)
[![Build](https://img.shields.io/badge/build-status-73BA25?style=for-the-badge&logo=opensuse)](https://build.opensuse.org/project/show/home:ackerman)

**Bleeding-edge Wayland packages for openSUSE Tumbleweed, Debian Forky and Debian Sid**

Curated packages optimized for minimal Wayland packages. Recipes live in [obs-nexus](https://github.com/Ackerman-00/obs-nexus) and are built on the [openSUSE Build Service](https://build.opensuse.org/project/show/home:ackerman).

> [!NOTE]
> All targets: `.rpm` and `.deb` packages are published on the
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

One source tree builds for three targets on OBS, **x86_64 only**
(owner decision 2026-10-11: i586/aarch64 removed from all recipes and repos;
Leap 16.0, Slowroll and Debian 13 Trixie dropped the same day, Ubuntu 26.04
dropped 2026-10-12):

| Family | Targets | Recipe |
|---|---|---|
| RPM (zypper) | openSUSE Tumbleweed (x86_64) | `*.spec` |
| DEB (apt) | Debian Testing (Forky), Debian Unstable (Sid) (amd64) | `<pkg>.dsc` + flat `debian.*` + orig tarball - ONE recipe builds both |

---

## Packages

| Package | Description |
|---|---|
| **bibata-cursor-theme** | Open source, compact, material designed cursor set
| **craft-launcher** | App launcher for the Craft suite
| **concat** | Free and open source video editor
| **concat-unstable** | Video editor main-branch snapshot (native source build)
| **fluxer** | Free and open source messaging & VoIP platform
| **helium-browser** | Private, fast, and honest Chromium-based browser
| **localsend** | Open source cross-platform alternative to AirDrop
| **lazyvim-git** | Neovim setup for lazy people (rolling git snapshot)
| **mangowm** | Scrollable-tiling Wayland compositor (dwm-like, wlroots-based)
| **matugen** | Material You color generation tool
| **obsidian** | Knowledge base for plain-text Markdown notes
| **openchamber** | Agentic development environment boards for issues and pull requests
| **opencode-desktop** | Open source AI coding agent
| **protonplus** | Wine and Proton-based compatibility tools manager
| **rootapp** | Discord alternative for gaming communities and large groups
| **scenefx** | Wayland compositor effects library (for wlroots 0.20)
| **stoat-desktop** | Open source, user-first chat platform desktop client
| **vesktop** | Custom Discord client with Vencord preinstalled
| **wlroots** | Modular Wayland compositor library (0.20 series)
| **zen-browser** | Minimal browser focused on privacy and calm browsing

---

## Build status

Automated OBS builds are triggered by the `update-packages.yml` pipeline (runs every 6h) which syncs changed packages to OBS and rebuilds them, and the autonomous opencode maintainer verifies and repairs failed builds on the same schedule.

| Project | Status |
|---|---|
| `home:ackerman` | [View builds](https://build.opensuse.org/project/show/home:ackerman) |
