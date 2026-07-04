---
name: adr-list-generation
description: Draft the proposed ADR catalog (adr-list.md) for a greenfield initiative before individual ADRs are written. Use at Foundation start after the initiative and product brief are approved.
---

# ADR List Generation Skill

## Purpose

Produce `initiatives/<slug>/adrs/adr-list.md` — a structured catalog of architecture decisions the initiative must make (or inherit) before drafting full ADRs with [`adr-maintenance`](../adr-maintenance/SKILL.md).

## When to Use

- Starting Foundation for a new initiative (after the initiative charter and product brief are approved)
- Refreshing the ADR catalog when scope, research, or dependencies change materially
- Before drafting any individual ADR-NNN

## Prerequisites

- `initiatives/<slug>/initiative.md` and `product-brief.md` exist and are approved
- Initiative Setup complete — release order captured in the product-brief Epic Index

## Required Inputs

| Input | Path / rule |
|-------|-------------|
| Initiative charter | `initiatives/<slug>/initiative.md` — Why, What, Success Criteria, **Depends On**, Reference |
| Product brief | `initiatives/<slug>/product-brief.md` — components, Epic Index (release order), explicit technical commitments |
| Research | Paths from initiative **Reference** table (e.g. `architecture/<slug>/`) |
| Architecture | Linked diagrams and design docs under `architecture/` |
| Tier 1 seed | Foundation-readiness categories: repo structure, branching, auth, API, data storage, deployment |
| Upstream catalogs | For each **Depends On** row: `initiatives/<dep>/adrs/adr-list.md` (+ individual ADRs when summaries are insufficient) |

## Required Workflow

1. Read initiative, product brief, research, and architecture docs listed in the initiative Reference table.
2. For each **Depends On** initiative, read `adrs/adr-list.md` and classify upstream decisions as **Inherited** (this initiative must conform; do not re-decide).
3. **Inventory decision candidates** from brief components, success criteria, research claims, and architecture layers.
4. **Classify each candidate:**
   - **Inherited** → Inherited constraints table only (repo-relative link; no local ADR ID)
   - **Local Proposed** → Proposed ADRs table with sequential `ADR-NNN`
   - **Deferred** → include with `(Phase N)` in summary when a later phase defers the decision
5. **Apply Tier 1 coverage** — every foundation-readiness Tier 1 category must map to a Proposed row or an Inherited constraint.
6. **Group thematically** (Core, Security, Data, Deployment, …).
7. **Deduplicate** — one decision per row; merge overlaps; rejected alternatives belong in full ADRs later.
8. **Present the draft** for human review before writing files.
9. **Write** `initiatives/<slug>/adrs/adr-list.md` (create `adrs/` if missing).

## Output Format

```markdown
## Inherited constraints

| Source initiative | ADR | Constraint |
|-------------------|-----|------------|
| <dep-initiative> | [ADR-001 Title](../<dep>/adrs/adr-001-....md) | One sentence: why this bounds the initiative |

## Proposed ADRs — <Initiative Title>

### <Theme>

| ID | Title | Status | Summary |
|----|-------|--------|---------|
| ADR-001 | Decision Title | Proposed | One sentence, decision-oriented |
```

Rules:

- All Proposed rows start with `Status: Proposed`. (This is the ADR catalog's own status column — it is not a doc-level Status field, and is not synced anywhere.)
- Summary is one sentence — not implementation detail or rejected alternatives.
- Do **not** copy upstream ADR text into Proposed rows; link in Inherited constraints instead.
- Do **not** link to local ADR files that do not exist yet (optional after `adr-maintenance` creates them).
- Number IDs sequentially from ADR-001 with no gaps in the initial catalog.

## Cross-Initiative Reference Model

ADRs are **local and numbered per initiative**. Upstream decisions use **repo-relative markdown paths**. When [`adr-maintenance`](../adr-maintenance/SKILL.md) drafts a local ADR, repeat upstream paths under **Related ADRs** in the ADR `## Links` section.

**Resolving upstream links:** Older upstream catalogs may list `ADR-NNN` without per-row file links. When building Inherited constraints:

- If the upstream list links to `adr-NNN-*.md`, use that path.
- If not, glob or scan `initiatives/<dep>/adrs/adr-NNN-*.md` and link to the ADR file when it exists.
- If no ADR file exists yet (upstream decision still Proposed), cite `Source initiative / ADR-NNN` in the Constraint column — do not invent a file path.

## Quality Checklist

- [ ] Every Tier 1 foundation category covered (Proposed or Inherited)
- [ ] Every **Depends On** initiative reflected in Inherited constraints
- [ ] Every load-bearing product-brief commitment has a Proposed or Inherited row
- [ ] Research-backed Proposed rows name the planned research doc path (`initiatives/<slug>/research/adr-NNN-*.md`) or the upstream claim/doc being inherited
- [ ] No duplicate of upstream ADR content
- [ ] IDs sequential; human reviewed before commit

## Anti-Patterns

- Copying upstream ADR summaries into local Proposed rows
- Listing source file paths in the catalog (belongs in full ADR `Applies To`)
- Skipping Tier 1 because "we'll add ADRs later"
- Creating GitHub ADR issues before the catalog is approved
- Drafting full ADRs before `adr-list.md` exists

## Next Step

After catalog approval, draft individual ADRs with [`adr-maintenance`](../adr-maintenance/SKILL.md), one list row at a time.

## Verification

- [ ] File written to `initiatives/<slug>/adrs/adr-list.md`
- [ ] Inherited constraints and Proposed ADRs sections present
- [ ] Tier 1 coverage confirmed
- [ ] No placeholder template text
