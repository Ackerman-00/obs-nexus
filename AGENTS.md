# AGENTS.md — opensuse-nexus

Work-notes for AI agents and humans maintaining this repo.

## Self-healing sweep architecture (added 2026-08-21)

Three-layer defense-in-depth for package staleness and integrity:

### Layer 1: Deterministic Python sweep (`tools/teardown-sweep.py`) — AUXILIARY, NOT VERDICT

Pure stdlib helper the **agent calls** (not a separate CI gate). Downloads every
artifact, tears it apart (AppImage extract, .deb control, zip internals, Electron
.asar, `application.ini`, ELF `--version` probe), verifies checksums (sha256,
BLAKE2B+SHA512, SRI), reads internal versions vs upstream, and (2026-08) runs
`spec-cleaner`/`rpmlint`/`rpmspec -P` hooks for openSUSE. The agent IS the teardown — it must tear every `*.spec` + `*.changes` + `_service` apart itself, run `spec-cleaner` + `rpmlint` + `zypper` checks, produce the dependency audit table, and ensure excellent spec. Sweep is evidence, not a pass-anyway script; CI gate hard-fails if the agent skips it.

Key functions:
- `resolve_canonical_repo()`: detects GitHub forks via API `parent.full_name`,
  compares against canonical upstream (not the fork)
- `is_chromium_build_number()`: filters Chromium engine build numbers
  (first component >= 50) from version probes
- `is_template_version()`: auto-detects RPM macros (%{bumpver}, %{shortcommit0}),
  bash expansions, git snapshots — skips them automatically (no hardcoded lists)
- `versions_match()`: handles both prefix and suffix version alignment
  (e.g. Chromium `143.1.93.137` vs Brave `1.93.137`)
- `staleness_pv()`: strips +build, .git-hash, -r1, ^git, ~beta suffixes
- `repology_newest()`: queries Repology API (120+ repos) for ANY package
- `repology_dep_info()`: gets upstream version + status from Repology
- `osv_query()`: queries OSV.dev for known CVEs on ANY package
- `compute_libyear()`: computes libyear drift from GitHub release dates
- `fix_stale_pkg()`: mechanical auto-fix — sed version in ebuild/spec/nix/template
- `--autofix` flag: when STALE is detected, auto-fix and re-verify

Exit code = verdict. Exit 0 = all packages verified. Exit 1 = any
FAIL/MISMATCH/STALE/UNVERIFIED → CI opens an issue.

### Layer 1a: Distro index collision check (`tools/distro-collision-check.py`) — MANDATORY

Makes the owner rule "check the target's own index before shipping a package,
and re-check it every run" executable. Reads the live Tumbleweed OSS
`primary.xml` (served as `.zst` since 2026) plus Debian forky + sid
`Packages.gz`, then reports:

- lib* / *-devel shadowing a distro package → FAIL (the wlroots/scenefx
  latent-collision class; those packages must stay dropped / RPM-only)
- application or data package with the same name → WARN with both versions
  (legitimate bleeding-edge upgrade along the same package name)
- invariants: `wlroots` must not exist, `scenefx` must have no `.dsc`,
  every spec carries `ExclusiveArch: x86_64`, every `.deb` is
  `Architecture: amd64` except the owner-approved arch-independent recipes
  (bibata-cursor-theme, lazyvim-git, faugus-launcher)

Exit 0 = no shadowing violation. Network flakes downgrade the affected
index to a WARN, they never turn into a false PASS of a broken invariant.

### Layer 1b: Docker battle test + dependency sweep (`tools/docker-sweep.py`) — MANDATORY

Runs INSIDE the agent, clean containers for the THREE-target matrix every
run (`opensuse/tumbleweed`; `debian:testing`, `debian:sid`):
1. Downloads EVERY .rpm from OBS home:ackerman (TW repo) + reindexes
2. `zypper --no-gpg-checks in` + `ldd` + `--version` for each binary (5+ per run)
3. Battle-tests `ls -R` (all `*.spec`/`*.changes`/`_service`/`update.sh`) + `yaml` workflows + README `zypper addrepo` path
4. Reports `| package | zypper install | ldd | status |` — any fail = fix spec/README
5. DEB family (`--type debian --debdist both`; `debian:testing` and
   `debian:sid` images): for specs whose
   Source0 is an upstream .deb (derived via `grep -l '\.deb' */*.spec`),
   apt/dpkg-install the payload + ldd on BOTH — Forky (testing) +
   Sid; ONE `.dsc` recipe
   builds both (both post-t64, no per-distro forks)
6. Debian BUILD recipes: every prebuilt/binary package (deb/rpm/AppImage/
   zip/tarball Source0) carries `<pkg>.dsc` + flat `debian.*` + orig tarball
   (debtransform input, assembled at build time). update.sh maintains all
   three (.dsc Version/Tar, debian.changelog entry, orig artifact) on every
   bump plus an ensure-guard; per-package actions/cache in update-packages.yml
   preserves the gitignored tarballs across fresh checkouts

Key features:
- `trivy_scan_image()`: scans base images for CRITICAL/HIGH/MEDIUM CVEs
- `--scan-images` flag: enables Trivy CVE scanning
- No manual `rpm -qp` fallback — docker battle test is mandatory

### Layer 2: Agentic self-healing prompt (opencode-schedule.yml PROMPT) — MANDATORY

YOU are the sweep. The PROMPT's TEAR-APART + DOCKER BATTLE TEST is NOT optional.
It must:

1. Tear every `*.spec`/`*.changes`/`_service` apart itself (Source0 → extract → Cargo.toml/meson.build vs BuildRequires), run 2026 toolchain: `spec-cleaner` + `rpmlint`/`brp-check-suse` (openSUSE:Specfile_guidelines Aug 2026), `rpmspec -P`, `osc build` — log output
2. Produce mandatory `| package | upstream deps | in spec | missing | status |` for ALL packages in the repo (count via `ls -d */`, never hardcode)
   - OSV.dev vulnerability scan (CVEs on pinned version)
   - Repology freshness (outdated vs 120+ repos)
   - Libyear drift (years behind upstream, budget=20yr)
   - Auto-update tool hints (livecheck, autocopr, nix-update)
3. For each OUTDATED: use the suggested auto-update tool to fix it
4. For each FAIL/MISMATCH: re-download, verify checksum, update if re-released
5. LIBYEAR ENFORCEMENT: if >20 yr, prioritize highest-drift packages
6. Never close a teardown issue without passing sweep + evidence
7. False positive defense: fix the sweep script, never weaken checks

### Layer 3: CI gate + issue auto-open — ENFORCED

`gate_passes()` now hard-checks that `.opencode-relay.md` contains `run_id` + `status: complete` + `PACKAGE.*BR.*Req` / `deps-verified` / `dependency audit`.
If the agent skips the table, the job fails and retries with stronger model.

### Why this architecture

- **Deterministic + intelligent**: the sweep is pure Python (no LLM needed,
  no hallucination, fast). The agent handles complex cases that require
  reasoning about upstream changes.
- **Universal**: works for ANY package — Repology, OSV.dev, GitHub API,
  Trivy. No hardcoded skip lists or package-specific logic.
- **Self-healing**: genuinely stale packages get auto-fixed by the sweep's
  `--autofix` and/or the agent's investigation. False positives get caught
  and the sweep is improved.
- **Proof-or-Stop**: exit code = verdict. No claims without evidence.
  The sweep output is committed to the repo as a receipt.
- **Defense-in-depth**: even if one layer misses, the next catches it.
  Fork detection, template version detection, libyear budget, and
  Trivy CVE scanning prevent the known false positive classes.
