---
name: foundation-review
description: Readonly review against foundation-readiness checklist before first product code. Use at foundation-review stage.
---

# Foundation Review Skill

## Purpose

Verify Tier 1 ADRs, architecture docs, and dev environment meet [`checklists/foundation-readiness.md`](../../checklists/foundation-readiness.md).

## When to Use

- Orchestrator `foundation-review` stage
- Before epic/feature delivery begins

## Required Inputs

- ADR files, architecture docs, CI status

## Required Workflow

1. Walk foundation-readiness checklist item by item.
2. Report pass/fail with evidence paths.
3. List blocking gaps before first code.
4. Write report to manifest task outputs — no edits.

## Multi-Agent Delegation (Cursor)

| Field | Value |
|-------|-------|
| Stage | `foundation-review` |
| Activity type | ReviewArtifact + ReviewArchitecture |
| Readonly | yes |

## Verification

- [ ] Every checklist item addressed
- [ ] Blockers explicit
