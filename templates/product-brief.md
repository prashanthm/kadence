<!--
AGENT: Product brief — defines one capability under an initiative and registers epics at a glance.

Fill order: (1) Title + tagline, (2) Initiative pointer, (3) What This Capability Delivers,
(4) Who It's For, (5) Components, (6) Epic Index rows.

Epic Index columns:
- Epic: short human-readable name.
- Slug: descriptive-slug identity, file-safe (e.g. mcp-core). Must match the epic doc filename stem in epics/<slug>.md when that file exists. NO positional IDs.
- Outcome: one line — what "done" enables for users or the business (not a task list).
- Description: scope hint only; not acceptance criteria.
- Phase: release-order phase NAME (no dates), e.g. "Phase 1 — Core". The Epic Index is where release order lives; there is no separate roadmap doc.
- Epic doc: relative path epics/<slug>.md or — if not created yet.

Do NOT paste full acceptance criteria, full feature lists, or raw issue tables into Epic Index — use epics/<slug>.md and GitHub for detail. Dates/progress live on the GitHub Projects Roadmap / milestones, not here.

Cross-links: initiative.md (charter), epics/ (deep dive).

Strip this entire HTML comment when writing to initiatives/ or anywhere outside templates/ — scaffolding only; not part of the product artifact.
-->

# <!-- REPLACE: Capability Name -->

> <!-- REPLACE: One-sentence description of this capability -->

## Initiative

> Part of: <!-- REPLACE: [<initiative-slug>](../initiative.md) -->
> See: `initiatives/<slug>/initiative.md`

## What This Capability Delivers

<!-- REPLACE: 2-3 sentences describing what this capability enables and who it's for -->

## Who It's For

<!-- REPLACE: Target users or roles -->

## Components

| Component | Role |
|-----------|------|
| <!-- REPLACE --> | <!-- REPLACE --> |

## Epic Index

<!-- Release order lives here, by phase NAME (no dates). This is the roadmap. -->

| Epic | Slug | Outcome | Description | Phase | Epic doc |
|------|------|---------|-------------|-------|----------|
| <!-- REPLACE --> | <!-- REPLACE: <descriptive-slug> --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE: Phase name --> | <!-- REPLACE: epics/<slug>.md or — --> |
