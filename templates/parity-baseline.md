<!--
AGENT: Parity Baseline — the no-regression gate for a brownfield migration. Produced by the parity-baseline skill; lives at initiatives/<name>/parity-baseline.md.

Built from the extracted AS-IS feature inventory. Every keep/change AS-IS feature must appear — a missing row is an unguarded regression. Each parity check is observable and verifiable. Intentional behavior changes are recorded as acceptable deltas with rationale (retire items are NOT here — they go to the decommission plan).

Strip this entire HTML comment when writing to initiatives/ or anywhere outside templates/ — scaffolding only.
-->

# Parity Baseline: <!-- REPLACE: Initiative Name -->

> No-regression gate. Inventory source: [`assessments/<system>/features/`](../../assessments/<system>/features/). Gate checklist: [`checklists/parity-gate.md`](../../checklists/parity-gate.md).

## Capability Inventory

| AS-IS feature (slug) | Disposition | Parity check (observable behavior) | Verified by |
|----------------------|-------------|------------------------------------|-------------|
| <!-- REPLACE: asis-<system>-<feature> --> | <!-- REPLACE: keep / change --> | <!-- REPLACE: behavior that must hold on the target --> | <!-- REPLACE: test / manual check --> |

## Characterization Test Plan

<!-- REPLACE: tests written against current AS-IS behavior, run against both source and target to prove equivalence — what to capture, where the tests live, how they run. -->

## Acceptable Deltas

| Capability | Intended change | Rationale |
|------------|-----------------|-----------|
| <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> |

## Parity Gate

<!-- REPLACE: the condition that must be true before cutover is allowed (all keep/change checks pass, acceptable deltas confirmed). Ties to the migration plan's cutover step. -->
