<!--
AGENT: Source Inventory — the list of sources consulted for a brownfield assessment and whether each was reachable. Produced by the context-acquisition skill; lives at assessments/<system>/source-inventory.md.

Record every source as reachable or a gap. Gaps are real findings: they lower confidence in the assessment. Capture scope (repos/projects/spaces/channels), date range, and the MCP server used.

Strip this entire HTML comment when writing to assessments/ or anywhere outside templates/ — scaffolding only.
-->

# Source Inventory: <!-- REPLACE: System Name -->

> Point-in-time record of sources consulted for the AS-IS assessment. Drives confidence levels in downstream artifacts.

| Field | Value |
|-------|-------|
| **System** | <!-- REPLACE: system slug --> |
| **Assessment date** | <!-- REPLACE: date --> |
| **Date range covered** | <!-- REPLACE: e.g. last 24 months of history --> |
| **Topics / components searched** | <!-- REPLACE: e.g. OSDU provisioning, auth, multi-tenant --> |

## Sources

| Source | Status | Access (MCP / tool) | Scope queried | Notes |
|--------|--------|---------------------|---------------|-------|
| Code / IaC / config | <!-- REPLACE: Reachable / Gap --> | <!-- REPLACE: graphify + reads --> | <!-- REPLACE: repos --> | <!-- REPLACE --> |
| Git history / PRs | <!-- REPLACE: Reachable / Gap --> | <!-- REPLACE: git, gh --> | <!-- REPLACE: repos --> | <!-- REPLACE --> |
| Jira | <!-- REPLACE: Reachable / Gap --> | <!-- REPLACE: Atlassian MCP --> | <!-- REPLACE: projects --> | <!-- REPLACE --> |
| Confluence | <!-- REPLACE: Reachable / Gap --> | <!-- REPLACE: Atlassian MCP --> | <!-- REPLACE: spaces --> | <!-- REPLACE --> |
| Slack | <!-- REPLACE: Reachable / Gap --> | <!-- REPLACE: Slack MCP --> | <!-- REPLACE: channels --> | <!-- REPLACE --> |
| Web / URLs | <!-- REPLACE: Reachable / Gap / Not declared --> | <!-- REPLACE: WebFetch / WebFetch + Playwright MCP --> | <!-- REPLACE: seed URLs, depth --> | <!-- REPLACE --> |
| Screenshots | <!-- REPLACE: N images / None --> | <!-- REPLACE: vision read --> | <!-- REPLACE: assessments/<system>/screenshots/ --> | <!-- REPLACE --> |

## Access Gaps & Impact

<!-- REPLACE: List each unreachable source and what it means for the assessment (which areas are under-evidenced, which findings stay Low confidence). If no gaps, state "None". -->
