# ⚡ Nexus (openSUSE)

[![OBS](https://img.shields.io/badge/OBS-home:ackerman-73BA25?style=for-the-badge&logo=opensuse)](https://build.opensuse.org/project/show/home:ackerman)
[![Build](https://img.shields.io/badge/build-status-73BA25?style=for-the-badge&logo=opensuse)](https://build.opensuse.org/project/show/home:ackerman)

**Bleeding-edge Wayland & gaming packages for openSUSE**

Curated packages optimized for minimal Wayland compositors (Niri, Mangowm) and high-performance gaming. Recipes live in [obs-nexus](https://github.com/Ackerman-00/obs-nexus) and are built on the [openSUSE Build Service](https://build.opensuse.org/project/show/home:ackerman).

> [!TIP]
> Packages update automatically — just run `sudo zypper dup` as usual.

---

## Installation

```bash
# 1. Add the OBS repository (as root)
zypper addrepo https://download.opensuse.org/repositories/home:ackerman/openSUSE_Tumbleweed/home:ackerman.repo
zypper refresh

# 2. Install a package (example)
zypper install zen-browser
```

> [!NOTE]
> Debian_Testing users: `.deb` builds are published on the
> [OBS project page](https://build.opensuse.org/project/show/home:ackerman).
> Slowroll is retired and no longer published.

### List available packages

```bash
zypper se --repo home_ackerman
```

Or **[browse all packages and their builds online](https://build.opensuse.org/project/show/home:ackerman)**.

---

## Packages

| Package | Description | Install |
|---|---|---|
| **bibata-cursor-theme** | Open source, compact, material designed cursor set | `sudo zypper install bibata-cursor-theme` |
| **fluxer** | Free and open source messaging & VoIP platform | `sudo zypper install fluxer` |
| **helium-browser** | Private, fast, and honest Chromium-based browser | `sudo zypper install helium-browser` |
| **localsend** | Open source cross-platform alternative to AirDrop | `sudo zypper install localsend` |
| **lazyvim-git** | Neovim setup for lazy people (rolling git snapshot) | `sudo zypper install lazyvim-git` |
| **matugen** | Material You color generation tool | `sudo zypper install matugen` |
| **obsidian** | Knowledge base for plain-text Markdown notes | `sudo zypper install obsidian` |
| **opencode-desktop** | Open source AI coding agent | `sudo zypper install opencode-desktop` |
| **protonplus** | Wine and Proton-based compatibility tools manager | `sudo zypper install protonplus` |
| **rootapp** | Discord alternative for gaming communities and large groups | `sudo zypper install rootapp` |
| **stoat-desktop** | Open source, user-first chat platform desktop client | `sudo zypper install stoat-desktop` |
| **vesktop** | Custom Discord client with Vencord preinstalled | `sudo zypper install vesktop` |
| **zen-browser** | Minimal browser focused on privacy and calm browsing | `sudo zypper install zen-browser` |

---

## Build status

Automated OBS builds are triggered by the `update-packages.yml` pipeline (runs every 6h) which syncs changed packages to OBS and rebuilds them, and the autonomous opencode maintainer verifies and repairs failed builds on the same schedule.

| Project | Status |
|---|---|
| `home:ackerman` | [View builds](https://build.opensuse.org/project/show/home:ackerman) |
