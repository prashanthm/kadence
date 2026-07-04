---
name: pr-review
description: Production-grade code review with requirements cross-check, findings by severity, and merge recommendation. Readonly ReviewCode activity for review-batch.
---

# PR Review Skill

## Purpose

Review code for correctness, regressions, edge cases, and alignment with task/feature/epic/ADR requirements.

## When to Use

- Orchestrator `review-batch` — concern `code`
- Open PR linked to task issue

## Required Inputs

- PR URL
- Traceability chain: task spec, feature, epic, ADRs
- Reference: [`.github/prompts/pr-review.prompt.md`](../../.github/prompts/pr-review.prompt.md)

## Required Workflow

1. Read PR diff and description.
2. Findings first, severity ordered: Critical, High, Medium, Low — file/line, why, fix.
3. Cross-check Matrix: Requirement | Source | PR Evidence | Met/Partial/Missing.
4. Open Questions / Assumptions.
5. Merge Recommendation: Approve / Request Changes / Comment-only with rationale.
6. Write to `initiatives/<name>/.sdlc/reviews/<pr>-code.md`.

## Rules

- If no defects: state "No blocking findings found."
- Distinguish blocking vs nice-to-have.
- Readonly — no code edits, no merge.

## Multi-Agent Delegation

| Field | Value |
|-------|-------|
| Stage | `review-batch` |
| Activity type | ReviewCode |
| Parallel | yes — with other review concerns |
| Readonly | yes |

## Verification

- [ ] Findings with severity
- [ ] Cross-check matrix present
- [ ] Merge recommendation explicit
