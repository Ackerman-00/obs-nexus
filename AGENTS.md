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

## Model selection (free-model cascade)

- `bash tools/model-cascade.sh` — the free-model chain for this run, derived
  from the live catalog (`https://opencode.ai/inference/v1/models`); the first
  entry is the model that runs, the rest are fallbacks for quota/region
  blocks. Both workflows (`opencode.yml`, `opencode-schedule.yml`) read it —
  no model list is hardcoded anywhere.
- `tools/model-rank.txt` — the strength order, one id per line, best first,
  each id preceded by a `#` line giving its published score, source and the
  date it was checked. The order is set by the per-run web check in
  `tools/sweep-prompt.md` (step 8, MODEL RANKING), not by hand: independent
  published scores beat vendor claims, and a model with no score ranks below
  one that has a score.
- `tools/model-cascade.sh` EXCLUDE — the owner veto (`glm-5.3-flash-free`,
  `jev-1.13-free`). Vetoed ids stay out of `tools/model-rank.txt` even while
  the catalog lists them: `glm-5.3-flash-free` answers "Endpoint is
  unavailable" / 403 region errors and burns an attempt window.
- `tools/model-cascade.sh` prints NEW and RETIRED ids on stderr — a new free
  id must be scored and ranked by the next run, a retired one dropped.
- `opencode.json` carries the same ids so the CLI can resolve them, and
  enables the websearch provider the benchmark check needs.

## Comment policy (owner rule)

Comments are short `#topic` labels: one line, a few words, naming a constraint
the code cannot show. No incident narratives, no dated lesson logs, no
restated code, no commented-out code, no banners, no "why this exists"
essays. Keep a comment only when a future maintainer would delete working code
without it (a version floor, the WHY of a pin, a license/SPDX proof, a
harness gotcha).

## The completion contract must measure truth, not the presence of strings

A gate that greps for the STRING "install-test table" passes a table full of
FAIL cells, and "status: complete" plus a pile of greppable rows is cheaper to
produce than one real fix. The cheapest passing strategy wins when the machine
only counts strings, so the gate parses instead:

- ANY install-test verdict cell that is not PASS fails the run, unless it is
  EXTERNAL and a `GAP: external` line names that package. A FAIL cell next to
  a same-run install PASS is a contradiction and fails the run.
- Every run carries `defects-found: N` and `defects-fixed: M`; the gate
  requires M + external gaps >= N.
- Every package named on the `changed:` line needs a PASS row in the
  install-test table. A fix you did not install-test is a fix you did not prove.
- Every run carries at least 8 distinct `hunt: <category> - <what you ran>`
  lines. A category you did not run is a category you did not check.
- A verdict is a transcript of a command, never a summary of a belief.

Nothing counts repairs unless repairs are counted: a run that found 12 defects
and fixed 0 must not be indistinguishable from a run that found 0.

## The permission scopes come from actionlint and the schema, not the docs

The GitHub docs table for `permissions` lists keys GitHub's workflow validator
does not accept, and a file carrying one is refused at parse time: the push
shows up as a failed run with NO jobs and the workflow path as the run name,
so the agent that would fix it cannot run either.

- the KEY set is actionlint's: actions, artifact-metadata, attestations,
  checks, contents, deployments, discussions, id-token, issues, models,
  packages, pages, pull-requests, repository-projects, security-events,
  statuses.
- the VALUES per key are the schema's
  (https://json.schemastore.org/github-workflow.json,
  `definitions.permissions-event`): `vulnerability-alerts` and `models` take
  read|none, `id-token` write|none.

`tools/workflow-valid.py` is that rule in one place, with the vendored
`tools/permissions-schema.json`. RULE: run `bash tools/check-workflows.sh`
(YAML parse + actionlint + scope scan) before pushing any workflow change. If
actionlint and the docs disagree, actionlint wins.

## No owner approval gates

The scheduler is the owner: wildcard tool permissions, write-scope workflows,
bot commit identity, OBS credentials and self-merge are already configured.
The gate fails any relay line containing `needs-owner`, waiting-for-owner, or
approval markers, and `tools/verify-opensuse.sh` refuses `status: complete`
while its report is red. Only a missing/expired secret or a proven external
outage is a `GAP: external - ... [probe: ...]` plus one tracking issue -
never a request to a human.

## Direct-to-main pushes from outside

Other people and agents push straight to main while a run is in flight. RULE:
every run `git fetch origin` BEFORE build decisions and reviews the main
commits that are not its own, then reconciles that work into the run (rebase
onto it, verify the builds it triggered, review the diff as code). Never
rebase over others' commits and never discard them. An external commit that
broke a build is fixed forward, not reverted: reverting can destroy a real fix
that solves a real defect. A change outside the package's own files (an
install-time `%post` that rewrites system configuration) is flagged loudly -
silent acceptance and silent revert are both wrong.

## Container teardown harness rule

When a package is rebuilt in a clean container with `rpmbuild -bb`, the
SOURCES dir must contain the package directory's LOCAL files (Patch files,
extra Source files such as `.desktop`, policies, wrapper scripts), not only
what `spectool -g` downloads - spectool fetches URL-declared sources only. A
teardown that fails with "Cannot read ... .patch" or a missing Source1+ in
`%install` is therefore a HARNESS bug, not a package bug: check the package
dir for tracked files before touching the spec. Fix: `cp -a <pkgdir>/. SOURCES/`
before running spectool.

## A macro name inside a `#` comment still expands

RPM expands macros on every spec line before it decides the line is a comment,
so `# %meson_test wraps two tests` becomes the meson test command and rpmbuild
dies with `Unknown tag: /usr/bin/meson test ...` on a line that reads as a
comment. Name the constraint, not the macro: `# dbus-run-session wraps two of
the upstream tests`.

## Harness smoke probes must match what the harness installed

A bare `rpmbuild -bb` in a container does not always run the brp compression
step that OBS runs, so a smoke that asserts a compression-specific path
(`.../man1/foo.1.gz`) fails on a healthy package. Probe with a glob, or check
the published package for compression-specific paths; keep `rpm -V` and `ldd`
checks as the real verdict, and treat a probe that names a path the RPM does
not ship as a PROBE-BUG rather than a package failure.

## OBS API and upstream research receipts (verified 2026-11-18)

- `https://api.opensuse.org/build/home:ackerman/_result` answers **HTTP 401**
  unauthenticated (verified this date). A 401 is `UNVERIFIED`, never a clean
  build. `tools/obs-api-check.py` reports the exact status code and exits 0
  for that case; exit 1 only for a concrete defect.
- Documented OBS endpoints (api.opensuse.org/apidocs, OBS user guide
  2026-11-11): `GET /build/{project}/_result`, `...?lastsuccess=1`,
  `/build/{p}/{repo}/{arch}/{pkg}/_reason`, `_history`, `_statistics`,
  `/source/{p}/{pkg}?view=info` (source version + md5sums, the drift check),
  and `POST /{p}?cmd=rebuild`. Use them instead of scraping the web UI.
- OBS source services can enforce checksums with `verify_file` + a `sha256`
  param in `_service`; a failed check makes the package `broken` (user guide
  ch. 7.4). Only add it where the spec actually pins a checksum.
- Published indices (verified HTTP 200 this date) are
  `download.opensuse.org/repositories/home:ackerman/openSUSE_Tumbleweed/repodata/repomd.xml`
  and `.../Debian_Testing/Packages.gz` / `.../Debian_Unstable/Packages.gz`.
  Debian binary names come from each `.dsc` `Binary:` field, not the directory
  (heroic-games-launcher ships as `heroic`).
- Debian ships `libscenefx-0.5` and `-dev` natively in sid and forky
  (packages.debian.org, fetched 2026-11-18). The old "scenefx is RPM-only"
  note is obsolete; no OBS DEB recipe is needed for that library.
- Repology API: max 1 request/s and a custom User-Agent containing a link to
  this repo plus its issue tracker, or bulk clients get blocked
  (repology.org/api, fetched 2026-11-18). 403 means a bad UA, not no data.
- OSV `POST /v1/querybatch` returns only advisory ids; fetch ranges from
  `GET /v1/vulns/{id}`, follow `next_page_token`, and group aliases before
  counting (osv.dev API docs, fetched 2026-11-18). No rate limit, but a 32 MiB
  response cap on HTTP/1.1.
- Debian QA floor: run `lintian` on the built `.deb`, prefer a clean chroot
  build (`sbuild`/`mmdebstrap`) over a host build, and keep
  `SOURCE_DATE_EPOCH` reproducibility (debian policy 4.15). On the RPM side,
  `rpmlint` on the SRPM has better coverage than on a bare spec; `spec-cleaner`
  enforces the openSUSE style (en.opensuse.org/openSUSE:Package_Cleaning).

## Tools in this repo (call these, do not hand-roll)

- `bash tools/check-workflows.sh` - YAML parse, actionlint, permission scopes,
  embedded-PROMPT sync, gate/verifier drift, argv guard and the 15-case
  verifier self-test. Run before pushing any workflow or contract change.
- `bash tools/verify-opensuse.sh` - external completion verifier; exit 1 means
  the relay is not done. Reads the current run's section only.
- `python3 tools/obs-api-check.py` - live OBS build state and published NVRs
  across Tumbleweed/Forky/Sid; 401 is UNVERIFIED, never clean.
- `python3 tools/hunt-obs.py [category ...]` - the same hunt categories as one
  command, one relay-ready `hunt:` line each, `UNVERIFIED` with the reason when
  a source is unreachable; `--selftest` runs offline.
- `bash tools/install-sweep.sh tools/probes.txt` - install + rpm -V/dpkg -V +
  ldd on all three targets; writes relay-ready PASS/FAIL rows.
- `bash tools/desktop-audit.sh <pkg> [tumbleweed|testing|sid]` - Icon/Exec
  resolution for shipped .desktop files.
- `bash tools/obs-drift.sh` - spec in git vs spec OBS built (needs OBS creds).
- `bash tools/spec-lint.sh` - rpmspec -P, rpmlint, spec-cleaner and debian.rules
  sanity in a clean Tumbleweed container.
- `python3 tools/fleet-invariants.py` - the invariants no single build can prove:
  `ExclusiveArch: x86_64`, the updater strip in every spec, `%attr(4755)` plus
  `override_dh_fixperms` wherever chrome-sandbox ships, `.dsc`/spec/control
  version+binary+Build-Depends+Debtransform-Tar agreement, a `.dsc` for every
  non-library package, README coverage, and a placeholder-only packager address.
  `--self-test` runs the 12 fixtures; `--root <dir>` scans another tree.

## Network-isolated OBS builds are an owned design decision

OBS build workers have no outbound network, but the GitHub Actions runner does.
A payload that needs network during build (issue #35, ladybird-unstable's ~40
vcpkg ports) is NOT an external blocker: the scheduler has full authority to
choose and implement the automated path. Default: build the payload on the
runner (larger runner or cached dependency image if a cold build is too slow),
upload a checksummed tarball to OBS, and let OBS repack offline, as
hermes-agent-desktop/build.sh does. Alternatives: vendor dependencies into the
source tree, or a dedicated AllowNetworkAccess subproject proven via API. Never
re-post "no action available" without a fresh command for each path; close the
tracking issue only after all three targets build and install-test PASS.

## Self-evaluating proposals in the scheduler prompt

A `BEGIN PROPOSAL` block is a design suggestion the scheduler must decide on
once, with evidence, not carry forever. On the deciding run it records
`proposal: accepted - landed: <commit>` or `proposal: rejected - <evidence>`.
If rejected, delete the whole block from both tools/sweep-prompt.md and the
embedded PROMPT; if adopted, implement it, verify on all three targets, then
rename the header to `STANDARD (done <date> <commit>) - see <workflow>`. Sync
both prompt copies, run tools/check-workflows.sh and commit either way.

## PikaOS compatibility (checked 2026-11-19)

PikaOS is Debian Sid + selected Debian Experimental + DEB Multimedia, all
rebuilt x86_64-v3/LTO/O3 and compiled against each other, plus a custom repo
(mesa, wine-staging, obs-studio, lutris, blender, kernel) and GFX/Compute
stacks (wiki.pika-os.com/en/faqs/pika-modifications, fetched 2026-11-19). It
reports codename `pika`, so third-party repo scripts need
`distro=debian codename=sid` (wiki install-debian-repos guide, same date).
Our Debian packages must be install-tested alongside that stack, not assumed
compatible. No usable container image was found on 2026-11-19 (Docker Hub
`pikaos/pikaos` 404; GHCR `pikaos-linux/pikaos` 401); packages.pika-os.com
answered HTTP 200. Record a `pikaos:` verdict table and a `hunt:
pikaos-compat` line with the exact commands. UNVERIFIED needs the status code,
never a clean claim.
