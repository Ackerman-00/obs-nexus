---
name: rpm-copr
description: OBS build logistics for home:ackerman: sources, services, build results, logs, rebuilds and the three targets.
---

OBS is not COPR. Use the documented API: GET /build/home:ackerman/_result,
?lastsuccess=1, /build/{p}/{repo}/{arch}/{pkg}/_reason and _history,
/source/{p}/{pkg}?view=info for source drift, POST /{p}?cmd=rebuild.
Unauthenticated calls return 401 - report UNVERIFIED with the status code.
Use `osc` when credentials are present. Published repos:
openSUSE_Tumbleweed, Debian_Testing (forky), Debian_Unstable (sid).
Source services live in `_service`; `verify_file` with a sha256 param makes
OBS fail a bad checksum as `broken`. `download_files` alone does not verify.
`tools/obs-api-check.py` audits live build and published state.
