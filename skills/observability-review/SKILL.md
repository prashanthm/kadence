---
name: observability-review
description: PR observability review — logging, tracing, metrics for new code paths. Readonly for review-batch.
---

# Observability Review Skill

## Purpose

Verify new code paths include planned instrumentation per Tier 2 observability ADR and [`checklists/pr-gate.md`](../../checklists/pr-gate.md) Observability section.

## When to Use

- Orchestrator `review-batch` — concern `observability`

## Required Inputs

- PR diff (new code paths)
- Observability ADR and its instrumentation standards

## Required Workflow

1. Identify new runtime paths in diff.
2. Check logging, tracing, metrics per ADR standards.
3. Flag missing instrumentation with suggested fix.
4. Write to `initiatives/<name>/.sdlc/reviews/<pr>-observability.md`.

## Multi-Agent Delegation

| Field | Value |
|-------|-------|
| Stage | `review-batch` |
| Activity type | ReviewObservability |
| Readonly | yes |

## Verification

- [ ] New paths reviewed for instrumentation
- [ ] Gaps actionable
