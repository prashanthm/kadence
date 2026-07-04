<!--
AGENT: Epic — one themed body of work under an initiative.

Epic slug must match the Slug column for this row in initiatives/<slug>/product-brief.md Epic Index.

Fill order: Metadata → Problem → What We're Building → Who It's For → Diagrams (optional; follow Diagrams AGENT below) → Value → Acceptance Criteria → Features → Future Enhancements.
Identity is a descriptive slug — no positional IDs. The epic is joined to its GitHub issue by slug + branch; the issue links back to this doc — no issue number stored here. Dates/progress live on GitHub Projects / milestones, not here.

Strip scaffolding-only `<!-- AGENT: ... -->` and HTML comments that say to strip when materializing into `initiatives/` — initiative epic files must be product content only.
-->

# <!-- REPLACE: Epic Name -->

## Metadata

When this file lives at `initiatives/<initiative>/epics/<this-file>.md`, use relative links to sibling initiative docs.

| Field | Value |
|-------|-------|
| **Slug** | <!-- REPLACE: <descriptive-slug> — matches the Epic Index Slug column and this file's stem --> |
| **Initiative** | <!-- REPLACE: [../initiative.md](../initiative.md) --> |
| **Product brief** | <!-- REPLACE: [../product-brief.md](../product-brief.md) (Epic Index is in this file) --> |
| **Owner** | <!-- REPLACE: Product Owner or delegate, or TBD --> |

> Joined to its GitHub issue by slug + branch; the issue links back here — no issue number stored in this file.

## Problem

<!-- REPLACE: What problem does this product area solve? Who has it? -->

## What We're Building

<!-- REPLACE: Plain English description — no implementation detail -->

## Who It's For

<!-- REPLACE: Target user or role -->

<!-- AGENT: Diagrams — When scaffolding or expanding this epic: (1) Include `## Diagrams` below only if scope boundaries, multi-system context, or ordering would be unclear without a visual. (2) Prefer fenced `mermaid` blocks in this file; if the product-brief already has the right diagram, link to it (e.g. `[product-brief.md](../product-brief.md#...)` ) instead of duplicating. (3) Do not add decorative-only diagrams. (4) If diagrams are not needed, remove the entire `## Diagrams` heading and any placeholder under it. (5) Files under `initiatives/` must be product content only: do not leave `<!-- AGENT: ... -->` comments in the delivered file — apply the instructions and emit real markdown or omit the section. -->
## Diagrams

<!-- REPLACE: Optional — one Mermaid diagram, or a short "See [../product-brief.md](../product-brief.md)" link to an existing figure, or delete this section -->

<!-- Value = outcomes and benefits ("why it matters"). Do not paste acceptance-criteria checklists here. -->
## Value

- <!-- REPLACE: Business or user outcome 1 -->
- <!-- REPLACE: Business or user outcome 2 -->
- <!-- REPLACE: Optional outcome 3 — add or remove bullets; prefer 2–5 concrete outcomes -->

<!-- Acceptance Criteria = verifiable "epic done" conditions. Each feature issue should eventually map to one or more ACs. -->
## Acceptance Criteria

- [ ] <!-- REPLACE: Verifiable outcome 1 -->
- [ ] <!-- REPLACE: Verifiable outcome 2 -->
- [ ] <!-- REPLACE: Verifiable outcome 3 — add or remove items as needed -->

<!-- Features = planned deliverables that roll up to this epic; tie each feature to ACs in feature docs or issues. Slug is a descriptive-slug identity, file-safe, and matches features/<slug>.md when you add feature docs. NO positional IDs. -->
## Features

| Feature | Slug | Description | Phase |
|---------|------|-------------|-------|
| <!-- REPLACE: short name --> | <!-- REPLACE: e.g. core-report-gen --> | <!-- REPLACE --> | <!-- REPLACE: Phase name --> |
| <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> |

<!-- Deferrals: name dependency or trigger (e.g. "after baseline ships"), not only "later". -->
## Future Enhancements

- <!-- REPLACE: Capability deferred to a later phase and why -->

## Additional Context

### Relevant ADRs

- <!-- REPLACE: Link to ADR file path and short reason it applies -->
