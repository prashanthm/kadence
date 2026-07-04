<!--
AGENT: Decommission Plan — safe retirement of the parts of the old system a migration replaces. Produced by the decommission-planning skill; lives at initiatives/<name>/decommission-plan.md.

Only retire dispositions from the migration plan belong here (keep/change are covered by the parity baseline). No teardown before the replacing capability passes the parity gate and consumers have migrated. Every retired item has a consumer-migration path and a verification step proving nothing live depends on it.

Strip this entire HTML comment when writing to initiatives/ or anywhere outside templates/ — scaffolding only.
-->

# Decommission Plan: <!-- REPLACE: Initiative Name -->

> Retirement source: migration-plan `retire` rows. Gate checklist: [`checklists/decommission-gate.md`](../../checklists/decommission-gate.md).

## Retirement Scope

| AS-IS item being retired (slug) | Component(s) | Reason |
|---------------------------------|--------------|--------|
| <!-- REPLACE: asis-<system>-<epic-or-feature> --> | <!-- REPLACE --> | <!-- REPLACE: replaced by ... --> |

## Consumers & Migration Paths

| Consumer / dependency | How it migrates off | Owner |
|-----------------------|---------------------|-------|
| <!-- REPLACE --> | <!-- REPLACE --> | <!-- REPLACE --> |

## Deprecation Timeline

| Step | Trigger / gate | Action |
|------|----------------|--------|
| Announce | <!-- REPLACE --> | <!-- REPLACE --> |
| Freeze (read-only) | <!-- REPLACE --> | <!-- REPLACE --> |
| Disable | <!-- REPLACE --> | <!-- REPLACE --> |
| Teardown | <!-- REPLACE: parity gate passed + consumers migrated --> | <!-- REPLACE --> |

## Data Handling

<!-- REPLACE: archive / export / delete plan per data store before deletion, per retention policy. -->

## Teardown

<!-- REPLACE: infrastructure teardown — IaC removal, account/resource cleanup, so the resource cannot drift back. -->

## Verification

<!-- REPLACE: how safe retirement is confirmed — no traffic, no live dependency, data archived. -->
