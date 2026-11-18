---
name: verification-before-completion
description: Final gate discipline: run the real verifier, prove every verdict cell and number, never write status complete on belief.
---

Before `status: complete`, run `bash tools/verify-opensuse.sh` with RUN_ID and paste the report. It checks the run-scoped relay: dependency and correctness tables, install-test verdicts (any FAIL fails the run), EXTERNAL paired with `GAP: external ... [probe: ...]`, defect counts, 8 hunts, dated websearch, no owner waits. A number must be derived from a command (`ls */*.spec | wc -l`), never hardcoded. `bash tools/check-workflows.sh` must pass before push.
Proof ladder for a recipe change: rpmlint on the SRPM, spec-cleaner, lintian on the built .deb, clean-build evidence (OBS build result or sbuild), container install + smoke. A PASS string in the relay is not the command output.
