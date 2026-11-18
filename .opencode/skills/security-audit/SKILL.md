---
name: security-audit
description: Package and repository security review: OSV ranges, checksum pins, secrets, unsafe scriptlets, supply-chain floors.
---

Query OSV /v1/querybatch with a top-level `version` and a real ecosystem or none. It returns ids only: fetch GET /v1/vulns/<id>, re-check each range event (introduced/fixed/last_affected), follow next_page_token and group aliases before counting. No OSV rate limit, but a 32 MiB response cap over HTTP/1.1.
Repology needs a descriptive User-Agent linking this repo plus its issue tracker and <=1 req/s; 403 means bad UA, not no data.
openSUSE security: rpmlint rejects unauthorized PAM modules and setuid bits by file digest; a per-package rpmlintrc may filter only proven false positives. Electron chrome-sandbox must be 0755 root:root or removed; verify with a non-root launch test.
Verify every `# sha256:` pin against the artifact it names; a pin lagging the shipped version is a false receipt. Never commit secrets.

Sources: osv.dev API docs, repology.org/api, en.opensuse.org/openSUSE:Package_security_guidelines - fetched 2026-11-18.
