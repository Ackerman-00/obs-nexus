# Arch Linux packaging on OBS — research notes (2026-10-11)

Scope: what it takes to ALSO build Arch Linux packages in `home:ackerman` on OBS,
next to the existing Tumbleweed `.spec` and Debian `.dsc` recipes. Primary sources
only; every claim carries its URL. Nothing here was applied to the repo — this
file is the whole deliverable.

## TL;DR

- OBS has first-class Arch support: `PKGBUILD` build recipe → `arch` binary
  (`.pkg.tar.zst`) → `Repotype: arch` published repo
  (`.db.tar.gz` / `.files.tar.gz`).
- One OBS package dir can carry `.spec` + `.dsc` + `PKGBUILD` at the same time.
  OBS picks **one** recipe per repository based on the repository's configured
  `Type`. A single package can be scheduled for TW, Debian Testing/Sid and Arch
  simultaneously, with each repo consuming a different file.
- [extra] is the only sensible Arch target: `[community]` was merged into
  `[extra]` in 2023, and the old repos were deleted 2025-03-01.
- OBS's own base project for Arch is `Arch:Extra` (empty/abandoned since 2012),
  so the build root has to be bootstrapped by us via DoD repotype `arch`.
- There is **no `.SRCINFO` requirement and no changelog requirement** on OBS
  (unlike AUR), and **no debuginfo/lint equivalent** — Arch does debug via
  debuginfod and lint via `namcap`/`shellcheck` as local tooling, not OBS-side.
- Arch support is real but thin in places: `x86_64` only in practice, `pkgrel` is
  not auto-incremented, `checkdepends`/`optdepends` are ignored for deps,
  and local source files in the OBS package dir are ignored by
  `Build::Arch`'s dep parser.

## 1. Decision: target [extra], x86_64 only

- `community` was merged into `extra` during the git migration (2023); `extra`
  is now the single "everything not in core" repo maintained jointly by
  Package Maintainers and Arch Developers.
- On 2025-03-01 Arch removed `[community]`, `[community-testing]`, `[testing]`,
  `[testing-debug]`, `[staging]`, `[staging-debug]` from mirrors. Anything
  still referencing them breaks on `pacman -Sy`.
- Arch officially supports `x86_64` only; `arch=(any)` is the only other legal
  value, and mkepkg `arch=(...)` should be `'x86_64'` for official/AUR packages.

Sources:
- https://wiki.archlinux.org/title/Official_repositories (extra/core/multilib, community merge)
- https://archlinux.org/news/cleaning-up-old-repositories/ (2025-03-01 removal)
- https://wiki.archlinux.org/title/PKGBUILD#arch ("Arch officially supports only x86_64")

Consequence for us: repo name `Arch_Extra` (matching OBS's own
https://build.opensuse.org/project/show/Arch:Extra naming), path element
`<path project="home:ackerman:Arch:Base" repository="standard"/>`, and a DoD
`repotype="arch"` mirror of `core/os/x86_64` + `extra/os/x86_64`.

## 2. Per-package file list

Required in each `<pkg>/` dir alongside the existing `.spec`/`.dsc`/`debian.*`:

| File | Required? | Notes |
|---|---|---|
| `PKGBUILD` | yes | The build recipe. OBS parses `depends`, `makedepends`, `checkdepends`, `arch`, `pkgname`, `pkgver`, `source`, `*sums`. |
| `<pkg>.install` (aka the file `install=` points at) | only if hooks needed | `pkg_preinstall_arch()` sources `.INSTALL` from the SOURCES dir to build the post-install script; it only runs if the package is in `Runscripts:` in prjconf. |
| local patches / assets declared in `source=` | no | **Ignored by OBS.** `Build::Arch::get_assets()` only accepts `^https?://` entries; local files are neither deps nor assets. |

Explicitly **not** required by OBS:
- `.SRCINFO` — AUR/metadata tooling only. OBS never reads it. Generate it
  locally (`makepkg --printsrcinfo > .SRCINFO`) if we ever want to push to AUR,
  but do not add it to OBS.
- a changelog file. PKGBUILD's `changelog=` field names a file that pacman
  shows via `pacman -Qc`; OBS does not consume it.
- `.changes` / `debian.changelog` / `debian.control` — OBS just ignores files it
  doesn't need for the repo's `Type`.

Note the interface inversion: in RPM the `%files` list is what determines
package contents; in Arch there is no such list — everything in `$pkgdir` is
packaged. So the PKGBUILD's `package()` function must be exact.

Source: OBS User Guide §2.4 "Arch: pkg" — https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-package-formats

## 3. How OBS picks PKGBUILD vs .spec vs .dsc in one package

Two layers, and both matter.

**Layer A — the scheduler (`bs_srcserver`).** It matches exactly one recipe file
per repository, by extension, in this fixed order (first hit wins):

```
Chart.yaml → appimage.yml → PKGBUILD → APKBUILD → fissile.yml → simpleimage →
snapcraft.yaml → flatpak.{yml,yaml,json} → mkosi.*.conf → (docker by packid) →
<pkg>-<repo>.<ext> → <pkg>.<ext> → strip packid components → any *.ext →
debian.control
```

- `$files{'PKGBUILD'} if $ext eq 'arch'` — only when the repo's type is `arch`.
- `Type:` in prjconf wins over filename sniffing; if `Type` is missing/UNDEFINED
  the job errors with `bad build configuration, no build type defined or detected`.
- The matched file becomes the job's `file`, and `Build::recipe2buildtype()`
  maps `PKGBUILD` → `arch` (also maps `debian.control` → `dsc`, `*.spec` → `spec`).
- Source services are unwrapped first: `_service:...:foo` names are mapped back
  to their real names before matching, so a service-generated PKGBUILD still
  matches.

Source: `src/backend/bs_srcserver` sub `findfile`
https://github.com/openSUSE/open-build-service/blob/master/src/backend/bs_srcserver#L982-L1035
and `Build::recipe2buildtype` in obs-build
https://github.com/openSUSE/obs-build/blob/master/Build.pm#L1276-L1297

**Layer B — the build script (`build-recipe`, `expand_recipe_directories`).**
When the repo config declares `type=arch` the script looks for `PKGBUILD` first,
then falls back to a fixed multi-extension list that includes both `.spec` and
`PKGBUILD`. It stops at the first extension that matches.

So: the *repository* decides, not the package. One package dir with
`foo.spec` + `foo.dsc` + `PKGBUILD` builds correctly for a `Type: spec` repo, a
`Type: dsc` repo, and a `Type: arch` repo — three jobs, one recipe each. Nothing
in the package needs to change. (Caveat: this is per *repository*; two repos with
the same `Type` in the same project would both pick the same file.)

Source: `build-recipe` `recipe_set_buildtype()` and `expand_recipe_directories()`
https://github.com/openSUSE/obs-build/blob/master/build-recipe#L121-L210

## 4. Build requirements / project config

prjconf for the Arch repo (in `home:ackerman/_config`, or better a dedicated
base project we own, since OBS's own `Arch:Extra` is dead):

```
Type: arch
Repotype: arch
```

Prerequisite, and this is the bootstrapping problem: OBS's stock Arch base
project `Arch:Extra` contains **zero packages** and its published repo has been
empty since 2012. The `core/os` + `extra/os` mirror URLs that
`obs-build/configs/arch.conf` hardcodes (`ftp.hosteurope.de`, `x86_64` only) are
similarly stale. So we must supply our own build root, e.g. project
`home:ackerman:Arch:Base` with a DoD repo:

```xml
<repository name="standard">
  <download arch="x86_64" url="https://geo.mirror.pkgbuild.com/core/os/x86_64" repotype="arch"/>
  <download arch="x86_64" url="https://geo.mirror.pkgbuild.com/extra/os/x86_64" repotype="arch"/>
  <arch>x86_64</arch>
</repository>
```

with `Type: arch` / `Repotype: arch` / `Preinstall: pacman ...` in that base
project, and `home:ackerman`'s Arch repo `<path>`-ing to it.

Constraints found in code:

- Preinstall must include a `pacman` that can bring up the build root.
  `pkg_initdb_arch()` creates `/var/lib/pacman/sync/{core,extra,community}.db`;
  `pkg_install_arch()` calls `pacman -U --overwrite '*' -d -d --noconfirm`
  after commenting out `CheckSpace`/`DownloadUser` in `pacman.conf`
  (pacman cannot run chrooted).
- The build runs `chroot ... su -lc "makepkg --config ../makepkg.conf --skippgpcheck ..."`
  as `$BUILD_USER` with a generated makepkg.conf setting
  `BUILDDIR/PKGDEST/PACKAGER`. **`--skippgpcheck` is always passed**, so
  `validpgpkeys` is inert on OBS.
- `recipe_build_arch` runs makepkg **twice**: once for the binary, once with
  `--allsource` for a source package. Both land in `ARCHPKGS` and are shipped back.
- `TOPDIR=/usr/src/packages`; `recipe_resultdirs_arch` = `ARCHPKGS` only.
- `create_baselibs()` returns early for `arch` — no `-32bit`/`-64bit` variants.
- PGP signature checking is skipped; there is `BSConfig::sign` support for the
  repo db (`bs_publish` `createrepo_arch` signs `*.db.tar.gz`/`*.files.tar.gz`).
- Architecture support is `x86_64` in practice: `Build::Arch::parse` only emits
  deps for `_x86_64` and `_i686` variants and its arch allow-list maps the i586
  family to `i686`; `bs_publish` remaps OBS `i586` → `i686` for arch packages.
- Only `pacman`/`arch` binaries for x86_64 and i586/i686 are recognised by the
  `pkg_install_arch` path (`.init_b_cache/rpms/pacman.arch`).

Sources:
- OBS User Guide §4.2 keywords (`Type:`, `Binarytype:`, `Repotype:`, `Preinstall:`)
  https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-prjconfig
- OBS User Guide §2.4 (PKGBUILD/makedepends parsing, no subpackages)
  https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-package-formats
- `build-pkg-arch` https://github.com/openSUSE/obs-build/blob/master/build-pkg-arch
- `build-recipe-arch` https://github.com/openSUSE/obs-build/blob/master/build-recipe-arch
- `Build/Arch.pm` https://github.com/openSUSE/obs-build/blob/master/Build/Arch.pm
- `configs/arch.conf` https://github.com/openSUSE/obs-build/blob/master/configs/arch.conf
- OBS DoD docs incl. the `repotype="arch"` example
  https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-concepts#concept-dod
- `bs_dodup` `dod_arch()` (requires URL ending in `<repo>/os/`, fetches `<repo>.db`)
  https://github.com/openSUSE/open-build-service/blob/master/src/backend/bs_dodup#L370-L381

### 4.1 Arch-side build requirements (what `makepkg` assumes)

The OBS-provided build root has to satisfy what `base-devel` gives an Arch
packager, because PKGBUILDs assume it. `configs/arch.conf` mirrors
`https://archlinux.org/groups/x86_64/base-devel/` with a reduced set:

- Required: `gcc-libs`, `glibc`
- Support: `gcc`, `autoconf`, `automake`, `binutils`, `bison`, `debugedit`,
  `fakeroot`, `flex`, `groff`, `libtool`, `m4`, `make`, `patch`, `pkgconf`,
  `sudo`, `texinfo`, `which`

Rules that follow from the Arch docs and directly affect PKGBUILDs we write:

- `base-devel` deps must **not** appear in `makedepends`.
- Use `--prefix=/usr` in builds; never install into `/usr/local`.
- `pkgver` may not contain `-` (upstream hyphens → `_`).
- `depends` must list direct libs; use `find-libdeps(1)` (devtools) to find them.
- List all external shared libs in `provides` (`find-libprovides(1)`).
- Don't add `$pkgname` to `provides`/`conflicts`.
- Licenses must be SPDX identifiers; custom license text goes to
  `/usr/share/licenses/$pkgname`.
- Don't introduce new PKGBUILD variables/functions unless unavoidable, and
  prefix any unavoidable ones with `_`.
- Don't use makepkg's own subroutines (`msg`, `msg2`, `error`, `warning`, ...).
- `make DESTDIR="$pkgdir" install`, not `make install`.
- No `/bin`, `/sbin`, `/dev`, `/home`, `/srv`, `/media`, `/mnt`, `/proc`,
  `/root`, `/selinux`, `/sys`, `/tmp`, `/var/tmp`, `/run` in packages.
- Sources must be HTTPS where possible and verified; don't drop checksums/PGP
  because upstream had a bad release.

Sources:
- https://wiki.archlinux.org/title/Arch_package_guidelines
- https://wiki.archlinux.org/title/Creating_packages
- https://wiki.archlinux.org/title/PKGBUILD
- https://man.archlinux.org/man/PKGBUILD.5

### 4.2 PKGBUILD contents Arch expects vs OBS reads

Only these are parsed by OBS for scheduling:
`pkgname`, `pkgver`, `arch`, `depends`/`makedepends`/`checkdepends`
(+ `makedepends_x86_64` etc.), `source`, `source_x86_64`, `sha512sums`/
`sha256sums`/`sha1sums`/`md5sums` (+ `_x86_64`/`_i686` variants).

Note `checkdepends` **is** parsed for deps but check deps are only installed
when a `check()` function exists. `optdepends`, `provides`, `conflicts`,
`replaces`, `groups`, `backup`, `options`, `install`, `noextract`, `validpgpkeys`
are **not** parsed for scheduling — they matter only inside makepkg.

Also note: `Build::Arch::get_assets` skips every `source` entry that is not
`https?://`. Local files placed in the OBS package directory are never treated
as remote assets. Practical consequence for this repo (all our packages ship
binary payloads via `Source0`): the Arch recipe must download its own payload
with `makepkg`'s own fetch (via `source=(https://...)` with a real checksum),
because OBS will not pre-seed a local file the way rpmlintrc/Source1 works for
RPM. That is the single biggest difference in effort per package.

## 5. Source services

The existing `_service` files in this repo use `download_files`
(`localsend/_service`) and `obs_scm`/`cargo_vendor` chains (`matugen/_service`).
None of that is Arch-specific; services are format-agnostic and produce files in
the package directory. What changes:

- OBS unwraps `_service:<svc>:<filename>` → `<filename>` before recipe matching,
  so a service-generated PKGBUILD is found (`bs_srcserver` `findfile`).
- `download_files`, `tar_scm`, `recompress`, `set_version` are the relevant
  services. There is **no** `updpkgsums`-equivalent service and no
  `bump-pkgrel` equivalent for Arch on OBS.
- If a service produces `PKGBUILD` alongside the `.spec`, the scheduler will
  still only pick one per repo — no conflict.
- Caution already encoded in `update-packages.yml`: packages whose services are
  all `mode="disabled"` lose regenerable sources on a fresh sync. An Arch
  variant of that logic would need to keep `*.pkg.tar.*`/`*.src.tar.gz`
  artifacts out of the "regenerable" set, or regenerate them.

Source: OBS User Guide §7 source services
https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-source-services
and `findfile` unwrapping at bs_srcserver#L986-L995.

## 6. debuginfo / lint equivalents

**debuginfo: none on OBS.** OBS's `debuginfo` flag only affects RPM builds.
`bs_worker` drops `-debuginfo`/`-debugsource` named binaries from the package
list when `nodbgpkgs` is set, and Arch packages never have those names.
`create_baselibs()` returns immediately for `BUILDTYPE == arch`.
Arch's answer to debug info is **debuginfod** — symbols served from
`https://debuginfod.archlinux.org/`, enabled by debuggers, with debug symbols
available only for a subset of packages. OBS neither generates nor consumes it.

Source:
- https://archlinux.org/news/debug-packages-and-debuginfod/
- https://wiki.archlinux.org/title/Debuginfod
- `bs_worker` L1828 `next if $nodbgpkgs && $bin =~ /-(?:debuginfo|debugsource)-/`
  https://github.com/openSUSE/open-build-service/blob/master/src/backend/bs_worker#L1820-L1832
- `build-pkg-arch`/`build-recipe-arch` — no `--debug` handling for arch.

**lint: none on OBS.** There is no `rpmlint`/`lintian` equivalent wired into the
Arch build path. The Arch-native tools are local/CIside:
- `namcap PKGBUILD` and `namcap <pkg>.pkg.tar.zst` (dep check, ELF/ldd scan,
  hierarchy, redundant deps).
- `shellcheck --shell=bash --exclude=SC2034,SC2154,SC2164 PKGBUILD`.
- `makerepropkg <pkg>.pkg.tar.zst` (devtools) or `repro -f ...` (archlinux-repro)
  for reproducibility.
- `updpkgsums` / `makepkg -g` for checksum refresh.

Sources:
- https://wiki.archlinux.org/title/Namcap
- https://wiki.archlinux.org/title/PKGBUILD#Integrity
- https://wiki.archlinux.org/title/Arch_package_guidelines#Reproducible_builds

## 7. What the update.sh-equivalent must maintain

`localsend/update.sh` and `matugen/update.sh` currently do: version check →
`sed` spec `Version:`/`Release:` → `sed` Source0 URL → refresh `.dsc`
`Version:`/`Debtransform-Tar:` → prepend `debian.changelog` → prepend `.changes`.
That model does not translate to Arch:

| Existing step | Arch equivalent |
|---|---|
| `sed Version:/Release:` in `.spec` | `sed pkgver=` / `pkgrel=` in `PKGBUILD` |
| Source URL bump in `Source0` | `source=(...)` bump; OBS does no macro expansion, so the URL must be literal or `${pkgver}`-templated |
| checksum refresh (`sha256sums`/`b2sums`) | **new work** — `updpkgsums` (pacman-contrib) or `makepkg -g >> PKGBUILD`. Neither runs on OBS. |
| rebuild gitignored orig wrapper tarball | none needed (no orig tarball in Arch) |
| `.dsc` `Debtransform-Tar:` + `debian.changelog` | none. There is no `.dsc`-style metadata and OBS reads no changelog |
| `.changes` prepend | none |
| `pkgrel` reset to 1 on upstream bump, `+1` on recipe-only fix | **manual only** — OBS does not auto-increment `pkgrel` (this exact gap is the top request on `Arch:Extra`: https://build.opensuse.org/project/show/Arch:Extra). |
| `--allsource` src package | produced automatically by OBS at build time; do not generate or commit it |

Also note: because `pkgrel` is manual, a recipe fix needs a `pkgrel` bump
committed in the repo, and `updpkgsums` needs to run locally before commit (or in
CI on a machine that has pacman-contrib). And because `source` entries must be
`https?://` to be treated as assets at all, the "orig wrapper + download_files"
pattern this repo uses for binary payloads has to be re-expressed as a real
`source=(https://...)` with real checksums.

Additional risk to track: `update-packages.yml`'s `sync_files()` protects
gitignored artifacts from being wiped on fresh checkouts. If we ever cache the
built `.pkg.tar.zst` in CI, the same guard must extend to `*.pkg.tar.*`,
`*.src.tar.gz` and the Arch `*.db`.

## 8. Open questions and how to verify each

1. **Does OBS's scheduler treat PKGBUILD and `.spec` in the same package as
   conflicting, or does it just pick per repo?** Code says pick-per-repo, but the
   "no more than one recipe per package" behaviour in the UI is worth confirming.
   Verify: `osc r` a scratch package containing both into a `Type: arch` projekt,
   check `osc api /build/<prj>/<repo>/x86_64/<pkg>/_jobhistory` shows one job and
   `bs_srcserver`'s `findfile` log line names `PKGBUILD`.
2. **Can `Source0`-style local files be used at all in the Arch recipe?** Code
   says no (`get_assets` requires `https?://`).
   Verify: drop a local tarball next to a PKGBUILD that lists it in `source=()`
   with a matching `sha256sums`, and read the build log of
   `makepkg -so`: if OBS passes the file through, it will be in `SOURCES/`.
3. **Does `--allsource` actually produce a usable `.src.tar.gz` on OBS?**
   `recipe_build_arch` runs it unconditionally.
   Verify: build any Arch package and `osc api .../ARCHPKGS` list the result.
4. **Exact `base`/`base-devel` closure needed.** `configs/arch.conf` is a
   *standalone-build* config; OBS uses the prjconf we give it, so the list must
   be written into `Preinstall:`/`Required:`/`Support:` of our base project.
   Verify: create `home:ackerman:Arch:Base` with the DoD repos and the
   `configs/arch.conf` package lists, then build a trivial PKGBUILD against it.
5. **i686/i586 viability.** `bs_publish` remaps `i586`→`i686`, and
   `Build/Arch.pm` handles the `_i686` dep array, but Arch itself ships no i686
   repo and `configs/arch.conf` only sets `RepoURL` for `%ifarch x86_64`.
   Verify: try `<arch>i586</arch>` in the base project and see whether pacman
   resolves; if not, restrict to `x86_64`.
6. **`pkgrel` auto-increment.** Not implemented upstream.
   Verify: https://github.com/openSUSE/open-build-service/issues?q=arch+pkgrel —
   open a search; the `Arch:Extra` feature request comment is the reference.
7. **Is `checkdepends` installed when `check()` exists?** Parsed for deps, but
   whether the resolver *installs* it under OBS is unverified.
   Verify: a PKGBUILD with `checkdepends=('shellcheck')` + a `check()` that runs
   `shellcheck`, and read the build log's package install list.
8. **Do `optdepends`/`provides`/`conflicts` reach the published repo db at all?**
   `bs_mkarchrepo` writes them from `.PKGINFO` of the built package, so they
   should — but the *scheduler* ignores them (only `depends/makedepends/
   checkdepends` are deps), which means no unresolvable-dep detection for
   provides/conflicts.
   Verify: `bs_mkarchrepo` L21-L36 mapping table vs `Build::Arch::parse` L146.
9. **Signing.** `createrepo_arch` signs `*.db.tar.gz`/`*.files.tar.gz` with
   `$BSConfig::sign` and writes `<reponame>.key`; the DoD `arch` repotype has
   **no** `<master>`/`sslfingerprint`/`pubkey` verification support (only
   susetags/rpmmd/deb do).
   Verify: publish and check for `.db.tar.gz.sig` + `.key` in the OBS download
   repo; confirm `pacman` accepts it with the project key.
10. **Arch mirror URL for DoD.** `dod_arch()` requires the URL to end with
    `<repo>/os/`. The URL used in the OBS docs example
    (`ftp5.gwdg.de/.../core/os/x86_64`) is illustrative.
    Verify: pick from https://archlinux.org/mirrors/ and `curl` the resulting
    `<repo>.db` before committing the project meta.

## 9. Not verified / known gaps

- I did not run any build. Everything above is from documentation and source
  code reading of OBS master and obs-build master plus the Arch wiki/news.
- OBS server version and the exact `obs-build` release used by
  build.opensuse.org were not confirmed (auth required for
  `/configuration`); API references are to the `master` branch.
- `bs_publish`'s `i586`→`i686` remap was read but not exercised.
- No Arch package was authored, so the effort-per-package estimate in §7 is
  structural (from what the parsers accept) rather than measured.

## 10. Source index

**OBS documentation**
- Supported Build Recipes and Package Formats (incl. "Arch: pkg"):
  https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-package-formats
- Build Configuration / prjconf keywords (`Type:`, `Binarytype:`, `Repotype:`,
  `Preinstall:`, `Required:`, `Support:`, `Prefer:`, `Runscripts:`):
  https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-prjconfig
- OBS Concepts — project meta, DoD repositories, the `repotype="arch"` example:
  https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-concepts
- Using Source Services (`_service` structure and modes):
  https://openbuildservice.org/help/manuals/obs-user-guide/cha-obs-source-services

**OBS source code**
- `findfile()` (recipe selection per repo/type) —
  https://github.com/openSUSE/open-build-service/blob/master/src/backend/bs_srcserver#L982-L1035
- `bs_srcserver` L1910-L1925 (type → findfile → recipe2buildtype → parse) —
  https://github.com/openSUSE/open-build-service/blob/master/src/backend/bs_srcserver#L1908-L1925
- `Build::recipe2buildtype` —
  https://github.com/openSUSE/obs-build/blob/master/Build.pm#L1276-L1297
- `recipe_set_buildtype()` / `expand_recipe_directories()` —
  https://github.com/openSUSE/obs-build/blob/master/build-recipe#L121-L210
- `Build/Arch.pm` (PKGBUILD parser, deps, exclarch, PKGINFO query) —
  https://github.com/openSUSE/obs-build/blob/master/Build/Arch.pm
- `Build/Archrepo.pm` (arch repo metadata parser) —
  https://github.com/openSUSE/obs-build/blob/master/Build/Archrepo.pm
- `build-pkg-arch` (pacman install/erase, `.INSTALL` handling) —
  https://github.com/openSUSE/obs-build/blob/master/build-pkg-arch
- `build-recipe-arch` (TOPDIR, makepkg.conf, `-so --skippgpcheck`, `--allsource`) —
  https://github.com/openSUSE/obs-build/blob/master/build-recipe-arch
- `build` L767 `BUILDTYPE == arch` skips baselibs; L1526 dist/repo selection —
  https://github.com/openSUSE/obs-build/blob/master/build#L761-L769 and #L1524-L1540
- `configs/arch.conf` (standalone Arch build config: Repotype, Preinstall,
  Required, Support, base-devel mirror list) —
  https://github.com/openSUSE/obs-build/blob/master/configs/arch.conf
- `dist/PKGBUILD` (reference PKGBUILD for obs-build itself) —
  https://github.com/openSUSE/obs-build/blob/master/dist/PKGBUILD
- `bs_mkarchrepo` (publishes `*.db` / `*.files` from built packages) —
  https://github.com/openSUSE/open-build-service/blob/master/src/backend/bs_mkarchrepo
- `bs_publish` `createrepo_arch` (signing, `i586`→`i686` remap) —
  https://github.com/openSUSE/open-build-service/blob/master/src/backend/bs_publish#L1233-L1270
- `bs_worker` L5094 `ARCHPKGS` result dir; L1828 debuginfo drop —
  https://github.com/openSUSE/open-build-service/blob/master/src/backend/bs_worker#L5090-L5098
- `bs_dodup` `dod_arch` (URL must end in `<repo>/os/`, fetches `<repo>.db`) —
  https://github.com/openSUSE/open-build-service/blob/master/src/backend/bs_dodup#L370-L381

**Arch Linux**
- PKGBUILD (variables, `.install`, integrity arrays) —
  https://wiki.archlinux.org/title/PKGBUILD
- PKGBUILD(5) man page — https://man.archlinux.org/man/PKGBUILD.5
- Creating packages — https://wiki.archlinux.org/title/Creating_packages
- Arch package guidelines — https://wiki.archlinux.org/title/Arch_package_guidelines
- Official repositories — https://wiki.archlinux.org/title/Official_repositories
- .SRCINFO — https://wiki.archlinux.org/title/.SRCINFO
- Namcap — https://wiki.archlinux.org/title/Namcap
- Debuginfod — https://wiki.archlinux.org/title/Debuginfod
- Arch mirrors list — https://archlinux.org/mirrors/
- News: Debug packages and debuginfod —
  https://archlinux.org/news/debug-packages-and-debuginfod/
- News: Cleaning up old repositories (2025-02-17) —
  https://archlinux.org/news/cleaning-up-old-repositories/

**OBS instance state**
- `Arch:Extra` project (base system project, 0 packages) —
  https://build.opensuse.org/project/show/Arch:Extra
