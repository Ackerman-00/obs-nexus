---
name: github-ops
description: Issue and PR triage with gh CLI; evidence in every comment, close only with proof, bot commit identity.
---

`gh auth status` first. Commit only as opencode-agent[bot] with the configured
author/committer env; never git config user.name/email, never --author, never
trailers. After every commit verify author and zero Co-Authored-By lines.
Fetch origin and pull --rebase before push. Fetch origin before build decisions
and review main commits that are not yours; reconcile them, never rebase over
them. Close an issue only after the fix is verified by a successful OBS build.
