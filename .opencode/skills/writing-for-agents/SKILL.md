---
name: writing-for-agents
description: Author and edit agent-consumed docs: AGENTS.md, sweep-prompt.md, SKILL.md; short labels, pointer-reached context, no stale claims.
---

Keep the embedded `PROMPT: |` in opencode-schedule.yml byte-identical to
tools/sweep-prompt.md (`bash tools/check-workflows.sh` enforces it). Write
rules that a machine can check; prose that cannot be falsified is not a check.
Keep comments to short `# topic` labels, no narratives or dated lesson logs.
When a rule changes, update gate, verifier, self-test and prompt in one commit.
