<!--
AGENT: Migration Plan — AS-IS -> TO-BE delta for a brownfield re-platform. Produced by the migration-planning skill; lives at initiatives/<name>/migration-plan.md.

Express the future as a delta against the recovered AS-IS model: keep / change / add / retire. Every TO-BE item traces to an extracted epic/feature disposition. Every step has a rollback. retire items carry into the decommission plan; keep/change items are covered by the parity baseline.

Strip this entire HTML comment when writing to initiatives/ or anywhere outside templates/ — scaffolding only.
-->

# Migration Plan: <!-- REPLACE: Initiative Name -->

> AS-IS source: [`assessments/<system>/`](../../assessments/<system>/). Gate: [`parity-baseline.md`](parity-baseline.md). Retirement: [`decommission-plan.md`](decommission-plan.md).

## Strategy

<!-- REPLACE: strangler-fig / parallel-run / big-bang cutover — and why, referencing the integration seams being swapped. -->

## AS-IS -> TO-BE Map

| AS-IS epic / feature (slug) | Disposition | Target | Notes |
|-----------------------------|-------------|--------|-------|
| <!-- REPLACE: asis-<system>-<capability-or-feature> --> | <!-- REPLACE: keep / change / add / retire --> | <!-- REPLACE: target epic/feature slug or component --> | <!-- REPLACE --> |

## Sequencing (seam by seam)

| Step | Seam swapped | Depends on | Rollback | Ships intact? |
|------|--------------|------------|----------|---------------|
| <!-- REPLACE: 1 --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE: Yes --> |

## Data Migration

<!-- REPLACE: sources, transforms, validation, and how data is kept consistent during the move. -->

## Cutover & Rollback

<!-- REPLACE: the cutover procedure and the rollback for each step; what triggers a rollback. -->

## Superseded Decisions

| Discovered ADR | Superseded by (migration ADR) |
|----------------|-------------------------------|
| <!-- REPLACE: assessments/<system>/adrs/NNN-... --> | <!-- REPLACE: docs/adrs/NNN-... --> |

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> |
