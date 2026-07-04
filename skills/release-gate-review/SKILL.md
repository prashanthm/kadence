---
name: release-gate-review
description: Readonly review against release-gate checklist before production ship. Use at release-review stage.
---

# Release Gate Review Skill

## Purpose

Verify release meets [`checklists/release-gate.md`](../../checklists/release-gate.md) across quality, security, traceability, observability, and release sections.

## When to Use

- Orchestrator `release-review` stage
- Before human ship decision

## Required Inputs

- Release scope, integration test results, release notes
- Staging verification evidence

## Required Workflow

1. Walk release-gate checklist by section.
2. Parallel concern review: quality, security, traceability ([`pr-traceability`](../pr-traceability/SKILL.md)), observability, release metadata.
3. Report pass/fail with evidence.
4. Write to `initiatives/<slug>/.sdlc/release-review.md`.
5. Request PO + Builder ship approval — do not deploy.

## Multi-Agent Delegation

| Field | Value |
|-------|-------|
| Stage | `release-review` |
| Activity type | ReviewArtifact + ReviewTraceability + ReviewObservability |
| Readonly | yes |

## Verification

- [ ] Full release-gate checklist covered
- [ ] Ship not executed by agent
