---
name: release-scope-planning
description: Define release scope from merged features and milestone goals. Use at release-plan orchestration stage.
---

# Release Scope Planning Skill

## Purpose

Document which features/tasks ship in a release, rollback criteria, and monitoring window — intent only, not a schedule.

## When to Use

- Orchestrator `release-plan` stage
- Before integration testing

## Required Inputs

- The phase name from the product brief's Epic Index (release order)
- Merged PRs / feature list for the phase
- Initiative release criteria

## Required Workflow

1. List features in scope, each with its `Part of epic:` link.
2. List explicit out-of-scope items.
3. Define rollback triggers and monitoring window duration.
4. Write scope doc to `initiatives/<slug>/.sdlc/release-scope.md`.
5. Request human approval of the scope before integration testing proceeds.

## Multi-Agent Delegation (Cursor)

| Field | Value |
|-------|-------|
| Stage | `release-plan` |
| Activity type | PlanRelease |

## Verification

- [ ] In-scope (with epic links) and out-of-scope explicit
- [ ] Rollback and monitoring defined
- [ ] Human approval requested before integration testing
