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
  https://download.opensuse.org/repositories/home:ackerman/openSUSE_Tumbleweed/ home:ackerman
sudo zypper refresh
sudo zypper install <package>
```

> [!NOTE]
> Use the repository baseurl form above. The older
> `.../home:ackerman.repo` file-URL form no longer works: current zypper
> no longer parses a remote `.repo` file at `addrepo` time and stores the
> file URL itself as the baseurl, so `zypper refresh` fails with
> "Repository type can't be determined" (verified in a clean
> `opensuse/tumbleweed` container, 2026-10-14).

The base distribution packages come from the standard Tumbleweed OSS
repository (`https://download.opensuse.org/tumbleweed/repo/oss/`).

### Debian Testing / Unstable

`.deb` builds are published on the
[OBS project page](https://build.opensuse.org/project/show/home:ackerman);
follow the "Download package" instructions there for your release.

The repository is signed - a bare `deb` line without the signing key fails
`apt-get update` with `Missing key A281D9E0...` on current Debian
(verified in clean `debian:testing` and `debian:sid` containers,
2026-10-18). Add the key once, then the source line:

```sh
sudo apt-get install ca-certificates curl gnupg
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.opensuse.org/repositories/home:ackerman/Debian_Testing/Release.key \
  | gpg --dearmor | sudo tee /etc/apt/keyrings/obs-nexus.gpg > /dev/null
echo "deb [signed-by=/etc/apt/keyrings/obs-nexus.gpg] https://download.opensuse.org/repositories/home:ackerman/Debian_Testing/ /" \
  | sudo tee /etc/apt/sources.list.d/nexus.list
sudo apt-get update && sudo apt-get install <package>
```

Use `.../Debian_Unstable/Release.key` for the Sid repository.

Package names are the source names in the table below, with one exception:
`heroic-games-launcher` installs under its binary name **`heroic`**
(verified in clean `debian:testing` + `debian:sid` containers,
2026-10-20: `apt-get install heroic` → `dpkg -V` clean; the
`heroic-games-launcher` name is not a valid Debian package name).

## Supported targets

One source tree builds for exactly three targets on OBS, **x86_64/amd64
only** (owner decision 2026-10-11: i586/aarch64 removed from all recipes and
repos; every other previously-listed target was dropped by owner order and is
out of scope):

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
| **faugus-launcher** | Lightweight app for running Windows games using UMU-Launcher
| **fluxer** | Free and open source messaging & VoIP platform
| **ghostty** | Cross-platform terminal emulator |
| **helium-browser** | Private, fast, and honest Chromium-based browser
| **heroic-games-launcher** | Open source GOG, Epic and Amazon games launcher (Debian binary package name is `heroic`; install with `apt-get install heroic`)
| **koharu** | Local-first ML-powered manga translator
| **localsend** | Open source cross-platform alternative to AirDrop
| **lazyvim-git** | Neovim setup for lazy people (rolling git snapshot)
| **mangowm** | Scrollable-tiling Wayland compositor (dwm-like, wlroots-based)
| **matugen** | Material You color generation tool
| **obsidian** | Knowledge base for plain-text Markdown notes
| **openchamber** | Agentic development environment boards for issues and pull requests
| **protonplus** | Wine and Proton-based compatibility tools manager
| **rootapp** | Discord alternative for gaming communities and large groups
| **scenefx** | Wayland compositor effects library (for wlroots 0.20) - RPM only; DEB builds take it from the distro's `libscenefx-0.5`
| **stoat-desktop** | Open source, user-first chat platform desktop client
| **vesktop** | Custom Discord client with Vencord preinstalled
| **zen-browser** | Minimal browser focused on privacy and calm browsing
| **cline-desktop** | Agentic AI coding agent desktop app (Tauri)
| **hyperframes-desktop** | HyperFrames Studio video editor (Electron)
| **omnirush-desktop** | OmniRush.ai desktop shell (Electron)

---

## Build status

Automated OBS builds are triggered by the `update-packages.yml` pipeline (runs every 6h) which syncs changed packages to OBS and rebuilds them, and the autonomous opencode maintainer verifies and repairs failed builds on the same schedule.

| Project | Status |
|---|---|
| `home:ackerman` | [View builds](https://build.opensuse.org/project/show/home:ackerman) |
