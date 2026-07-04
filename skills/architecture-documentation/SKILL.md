---
name: architecture-documentation
description: Draft system architecture docs under docs/architecture from ADRs and codebase context. Use at foundation-arch stage.
---

# Architecture Documentation Skill

## Purpose

Produce architecture documentation: system context, container/component views, key flows — grounded in Tier 1 ADRs.

## When to Use

- Orchestrator `foundation-arch` stage
- Foundation phase before first feature code

## Required Inputs

- Tier 1 ADRs
- Codebase or initiative technical context
- graphify report if available

## Required Workflow

1. Read accepted Tier 1 ADRs.
2. Draft system context diagram description (text/mermaid).
3. Document containers, components, key integrations.
4. Write under `docs/architecture/` — one file per view or combined overview.
5. Flag gaps needing ADR decisions.

## Multi-Agent Delegation (Cursor)

| Field | Value |
|-------|-------|
| Stage | `foundation-arch` |
| Activity type | AuthorArtifact |
| Parallel | sections in parallel if disjoint files |

## Verification

- [ ] Aligns with Tier 1 ADRs
- [ ] Team review requested
