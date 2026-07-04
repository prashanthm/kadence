<!--
AGENT: Feature — THE build unit. A shippable increment inside an epic.

The feature carries only product intent: What / Why / Acceptance Criteria / Depends On, plus a
`Part of epic:` link. Identity is a descriptive slug — no positional IDs. The feature is joined to
its GitHub issue by slug + branch; the issue links back to this doc — no issue number stored here.

Engineering detail (files, steps, edge cases, task breakdown) does NOT live in this file. It lives in
the code repo at `specs/<feature-slug>/` — see spec.md/plan.md/tasks.md there (Spec-Kit trio).

Strip this entire HTML comment when writing outside templates/ — scaffolding only.
-->

# <!-- REPLACE: Feature Name -->

> Part of epic: <!-- REPLACE: [<epic-slug>](../epics/<epic-slug>.md) -->
> **Slug:** <!-- REPLACE: <descriptive-slug> — file-safe stem for `features/<slug>.md`, e.g. core-report-gen -->

> Joined to its GitHub issue by slug + branch; the issue links back here — no issue number stored in this file.

## What

<!-- REPLACE: What this feature delivers — one paragraph -->

## Why

<!-- REPLACE: Which epic acceptance criterion does this satisfy? -->

## Acceptance Criteria

- [ ] <!-- REPLACE: Verifiable outcome 1 -->
- [ ] <!-- REPLACE: Verifiable outcome 2 -->

## Depends On

- <!-- REPLACE: Other feature, ADR, or infrastructure this requires — or "None" -->

<!-- AGENT: Diagrams — When scaffolding this feature: (1) Include `## Diagrams` only for interaction-heavy flows (e.g. auth sequence, tool registration, multi-step I/O). Skip for simple, well-described behavior. (2) Use fenced `mermaid` (sequenceDiagram, flowchart) or link to the parent epic or product-brief if the diagram already exists there. (3) Remove the whole `## Diagrams` section if not needed. (4) Feature docs under `initiatives/` must not retain `<!-- AGENT: ... -->` — replace with real content or delete the section. -->
## Diagrams

<!-- REPLACE: Optional — Mermaid or link to epic/product-brief; or delete section -->

## Implementation

> Engineering detail is NOT in this doc. It lives in the code repo at `specs/<feature-slug>/`:
> `spec.md` (behavior contract), `plan.md` (files, steps, ADRs, edge cases), and `tasks.md`
> (granular parallelizable units, each with a `## Loop AC`). See the `spec.md` template.
