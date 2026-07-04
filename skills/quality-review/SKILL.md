---
name: quality-review
description: PR quality review — tests, coverage, AC satisfaction, regression risk. Readonly for review-batch.
---

# Quality Review Skill

## Purpose

Verify PR meets quality bar: tests cover changed behavior, ACs satisfied, no obvious regressions.

## When to Use

- Orchestrator `review-batch` — concern `quality`

## Required Inputs

- PR diff and test file changes
- Linked task/feature ACs the PR claims to satisfy

## Required Workflow

1. Map changed behavior in the diff to tests added/updated.
2. Identify missing negative-path or integration coverage.
3. Check unit tests pass (from CI or local if available).
4. Verify the PR's changes satisfy the linked task/feature ACs.
5. Findings by severity; checklist pass/fail.
6. Write to `initiatives/<name>/.sdlc/reviews/<pr>-quality.md`.

## Multi-Agent Delegation (Cursor)

| Field | Value |
|-------|-------|
| Stage | `review-batch` |
| Activity type | ReviewArtifact |
| Readonly | yes |

## Verification

- [ ] Test coverage gap analysis present
- [ ] AC mapping explicit
