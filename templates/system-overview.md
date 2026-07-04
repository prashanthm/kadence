<!--
AGENT: System Overview — descriptive AS-IS snapshot of an existing system. Produced by the current-state-assessment skill; lives at assessments/<system>/system-overview.md.

This is the entry document of the AS-IS reference model. It is DESCRIPTIVE — current reality, not a program of work. Do NOT give it Status / Success Criteria / Timeline (that is an initiative.md). Cite evidence ledger ids for non-trivial claims and tag major findings with a confidence level (High/Medium/Low). Code wins for "what exists"; flag conflicts with docs/tickets, do not resolve them.

Fill order: System Summary -> Components -> Runtime Topology -> Integration Seams -> External & Cloud Dependencies -> Identity & Auth -> Data Stores -> Tech Debt & Risks.

Strip this entire HTML comment when writing to assessments/ or anywhere outside templates/ — scaffolding only.
-->

# System Overview: <!-- REPLACE: System Name -->

> AS-IS reference snapshot. Companion artifacts: [`source-inventory.md`](source-inventory.md), [`evidence-ledger.md`](evidence-ledger.md), [`epics/`](epics/), [`features/`](features/), [`adrs/`](adrs/).

## System Summary

<!-- REPLACE: 1-2 paragraphs — what the system does today, who runs it, who uses it. Cite evidence ids. -->

## Components

| Component / Service | Responsibility | Tech | Evidence | Confidence |
|---------------------|----------------|------|----------|------------|
| <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE: EV-ids --> | <!-- REPLACE: High/Med/Low --> |

## Runtime Topology

<!-- REPLACE: How components are deployed and talk at runtime. Prefer a mermaid diagram. Cite evidence ids. -->

## Integration Seams

<!-- AGENT: Seams are first-class — every place the system talks to something else is where a strangler-fig migration will cut. Name each one. -->

| Seam | From -> To | Protocol / Contract | Evidence | Confidence |
|------|-----------|---------------------|----------|------------|
| <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE: EV-ids --> | <!-- REPLACE --> |

## External & Cloud Dependencies

| Dependency | Used for | Provider | Evidence | Confidence |
|------------|----------|----------|----------|------------|
| <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE: EV-ids --> | <!-- REPLACE --> |

## Identity & Auth

<!-- REPLACE: How users/services authenticate and are authorized today. Cite evidence ids. -->

## Data Stores

| Store | Data | Engine | Evidence | Confidence |
|-------|------|--------|----------|------------|
| <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE: EV-ids --> | <!-- REPLACE --> |

## Tech Debt & Risks

<!-- REPLACE: Known debt, fragility, and risks — including assessment risks from source gaps (areas under-evidenced because a source was unreachable). Cite evidence ids; mark uncorroborated items Low. -->
