---
name: web-research
description: Mandatory live research; verify versions, URLs, dates, CVEs and host status from primary sources with exact status codes; never answer from memory.
---

Every external fact must carry a date and a source URL in the relay.
Search with 2-3 differently worded queries, then fetch the primary source: upstream release API, OBS API, openSUSE/Debian docs, OSV, Repology.
Quote the exact HTTP status when a host is blocked; a 401 on the OBS build API is UNVERIFIED, not clean. A 403 from Repology means a missing descriptive User-Agent. Record `hunt:` and `websearch:` tokens with the date and at least one https URL. Absence of a search result is not proof.
RPM macro facts such as "macros expand in comments" come from rpm.org/docs/latest/manual/spec.html (fetched 2026-11-18); do not rely on an old lesson when the primary doc is one fetch away.
