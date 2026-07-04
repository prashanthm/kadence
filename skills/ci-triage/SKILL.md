---
name: ci-triage
description: Diagnose CI failures on a feature branch and propose or apply minimal fixes. Use when verify-batch or PR checks fail.
---

# CI Triage Skill

## Purpose

Investigate failing CI checks, classify root cause, and either propose a fix plan or apply minimal patches within task scope.

## When to Use

- Orchestrator `ci-triage` stage
- After `verify-batch` reports failures
- Before `pr-open`

## Required Inputs

- CI log output or `gh run view` results
- Feature branch and changed files
- Linked task/feature (scope boundary for the branch)

## Required Workflow

1. Identify failing job(s) and first error in log.
2. Classify: test failure, lint, build, security scan, flaky.
3. If fix is within the linked task/feature scope — apply minimal fix.
4. If fix exceeds that scope — report gap; do not expand scope silently.
5. Re-run failed commands locally if possible.
6. Return triage report with status fixed|blocked|needs-scope-change.

## Multi-Agent Delegation

| Field | Value |
|-------|-------|
| Parallel-safe | No |
| Stage | `ci-triage` |
| Activity type | GatherContext + Implement |
| Task | `shell` for CI commands |

## Verification

- [ ] Root cause identified with log reference
- [ ] Scope respected
- [ ] Re-run result reported
