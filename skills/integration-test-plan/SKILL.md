---
name: integration-test-plan
description: Plan cross-feature integration test scenarios for a release scope. Use at integration-plan stage.
---

# Integration Test Plan Skill

## Purpose

Define integration test scenarios that verify features work together against release scope ACs.

## When to Use

- After release scope agreed
- Orchestrator `integration-plan` stage

## Required Inputs

- Release scope doc
- Feature ACs in scope
- [`checklists/release-gate.md`](../../checklists/release-gate.md) Quality section

## Required Workflow

1. Identify cross-feature seams and integration points.
2. Write scenarios: preconditions, steps, expected outcomes.
3. Map each scenario to feature/epic ACs.
4. Write plan to `initiatives/<name>/.sdlc/integration-test-plan.md`.
5. Update manifest `release.integration_plan_path`.

## Multi-Agent Delegation

| Field | Value |
|-------|-------|
| Stage | `integration-plan` |
| Activity type | PlanIntegrationTest |
| Parallel | scenarios can be authored in parallel Tasks |

## Verification

- [ ] Scenarios cover release scope ACs
- [ ] Cross-feature seams addressed
