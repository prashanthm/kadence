---
name: parity-verify
description: Verify TO-BE delivery against the parity baseline for brownfield cutover. Read-only — produces a report, never executes cutover.
---

# Parity Verify Skill

## Purpose

Check migrated/replaced capabilities against [`parity-baseline.md`](../../templates/parity-baseline.md) — no silent regressions at cutover.

## When to Use

- After TO-BE delivery, to check migrated/replaced capabilities against the parity baseline
- Before the brownfield cutover gate

## Required Inputs

- `initiatives/<name>/parity-baseline.md`
- AS-IS features from `assessments/<system>/features/`
- Evidence of TO-BE implementation (tests, demos, PRs)

## Required Workflow

1. Load parity baseline keep/change/retire map.
2. For each keep/change item, verify evidence in TO-BE.
3. Mark Met/Partial/Missing with evidence ids.
4. Write report to `initiatives/<name>/.sdlc/parity-verify-report.md`.
5. Human cutover decision — agent does not execute cutover.

## Notes

- Read-only: this skill inspects evidence and writes a report. It never executes cutover — that is a human decision.

## Verification

- [ ] Every baseline item has status
- [ ] Missing items flagged as regression risks
