---
name: systematic-debugging
description: Root-cause investigation before fixing: competing hypotheses, falsifying probes, attack the premise after two failed fixes.
---

State at least two competing hypotheses, run a command that can falsify each,
and paste the output. After two failed fixes, stop and re-research instead of
repeating. Distinguish a harness artifact from a package defect: a bare
rpmbuild -bb in a container is not the OBS builder, and a probe naming a file
the package does not ship is a PROBE-BUG, not a package FAIL.
