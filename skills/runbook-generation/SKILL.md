---
name: runbook-generation
description: Author operational runbooks for services under docs/runbooks. Use at runbook-batch stage.
---

# Runbook Generation Skill

## Purpose

Document operational procedures: deploy, rollback, troubleshoot, on-call steps for a service or component.

## When to Use

- Orchestrator `runbook-batch` stage
- Post-implementation or pre-release

## Required Inputs

- Architecture docs and ADRs (deployment model)
- Service name and repo path

## Required Workflow

1. Identify operational scenarios: deploy, rollback, common failures, escalation.
2. Write step-by-step procedures with commands and verification.
3. Link to observability dashboards and alerts.
4. Write to `<code-repo>/docs/runbooks/<service>.md`.

## Multi-Agent Delegation (Cursor)

| Field | Value |
|-------|-------|
| Stage | `runbook-batch` |
| Activity type | AuthorRunbook |
| Parallel | per service |

## Verification

- [ ] Deploy and rollback documented
- [ ] Escalation path clear
