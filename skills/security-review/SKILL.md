---
name: security-review
description: PR security review — SAST mindset, secrets, dependencies, auth. Readonly ReviewSecurity for review-batch.
---

# Security Review Skill

## Purpose

Review PR for security issues per [`checklists/pr-gate.md`](../../checklists/pr-gate.md) Security section.

## When to Use

- Orchestrator `review-batch` — concern `security`
- Parallel with other review Tasks

## Required Inputs

- PR diff and dependency changes
- Auth/secrets ADRs if applicable

## Required Workflow

1. Check: secrets in code, unsafe defaults, injection paths, auth bypass, dependency CVEs.
2. Findings by severity with file/line and fix.
3. Map to PR gate Security checklist items pass/fail.
4. Write to `initiatives/<name>/.sdlc/reviews/<pr>-security.md`.

## Multi-Agent Delegation (Cursor)

| Field | Value |
|-------|-------|
| Stage | `review-batch` |
| Activity type | ReviewSecurity |
| Readonly | yes |

## Verification

- [ ] PR gate Security checklist addressed
- [ ] Blocking issues clearly marked
