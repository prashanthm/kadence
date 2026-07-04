# Assessment Readiness Checklist

> Must pass before a brownfield AS-IS reference model is used to drive forward planning.

## Context Acquisition

- [ ] `assessments/<system>/source-inventory.md` lists every source as reachable or gap
- [ ] Scope (repos, Jira projects, Confluence spaces, Slack channels) and date range recorded
- [ ] MCP server named for each external source; unreachable sources logged as gaps with impact
- [ ] `assessments/<system>/evidence-ledger.md` has stable ids, locators, and summaries
- [ ] Contradictions between sources logged (not silently resolved)

## AS-IS Coverage

- [ ] `system-overview.md` covers components, runtime topology, integration seams, dependencies, identity, data stores, tech debt
- [ ] Discovered ADRs (`Status: Discovered`) capture the system's de-facto decisions, confirmed in code/IaC
- [ ] Extracted epics cover the in-scope capability surface
- [ ] Extracted features complete enough to serve as the parity inventory

## Quality

- [ ] Every extracted artifact cites evidence ledger ids (provenance)
- [ ] Each major finding carries a confidence level (High/Medium/Low)
- [ ] Source gaps reflected as assessment risks that lower confidence
