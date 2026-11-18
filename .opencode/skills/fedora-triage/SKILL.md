---
name: fedora-triage
description: openSUSE and Debian runtime triage with zypper/apt, systemd and OBS build logs, verified after each step.
---

When a built package fails at runtime, reproduce in a clean container first.
Map the symptom to the target: zypper for Tumbleweed, apt for forky/sid.
Inspect OBS build logs via the API `_log` endpoint or `osc buildlog`; a 401
must be reported, not guessed around. Check systemd units and file ownership
against the spec. Keep a rollback plan and verify after every change.
