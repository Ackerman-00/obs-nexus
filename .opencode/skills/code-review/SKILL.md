---
name: code-review
description: Evidence-backed review of specs, tools and workflow changes before they land; findings with location, proof and severity.
---

Review your own diff on two axes before pushing: Standards (AGENTS.md and the
scheduler contract) and Spec (what the task asked, nothing more). Fix findings
first. A change that only adds a string to a relay while leaving a FAIL cell
is not a fix. New tokens must be enforced in the gate, the verifier and the
prompt together, or the contract drifts.
