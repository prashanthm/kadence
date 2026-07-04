---
name: decommission-planning
description: Author a decommission plan (decommission-plan.md) for the AS-IS epics, features, and components a migration retires, with deprecation timeline, consumer migration, teardown, and verification. Use to safely retire the old system after a brownfield migration.
---

# Decommission Planning Skill

## Purpose

Plan the safe retirement of the parts of the old system a migration replaces — the `retire` dispositions from the migration plan. Covers which extracted epics/features/components go away (e.g. Multi-Tenant and Dedicated SaaS variants, the r3m25 OSDU-on-AWS stack), the deprecation timeline, consumer migration, teardown, comms, and verification that nothing live still depends on them.

## When to Use

- After `migration-planning`, to action every `retire` disposition
- Once the parity gate has cleared for the replacing capability
- Before tearing down infrastructure or removing code paths from the old system

## Required Inputs

- The `migration-plan.md` `retire` dispositions
- AS-IS epics/features under `assessments/<system>/` for the items being retired
- The system-overview (components, integration seams) and Evidence Ledger (consumers, dependencies)
- Template: [`templates/decommission-plan.md`](../../templates/decommission-plan.md)

## Required Workflow

1. Read [`templates/decommission-plan.md`](../../templates/decommission-plan.md) and treat every `<!-- AGENT: ... -->` block as authoring rules — not text to copy.
2. List the retirement scope: each AS-IS epic/feature/component being retired, traced from the migration plan's `retire` rows.
3. For each item, identify live consumers and dependencies from the system-overview seams and the ledger; define how each consumer migrates off.
4. Build the deprecation timeline: announce -> read-only/frozen -> disable -> teardown, with the trigger/gate for each step.
5. Plan data handling (archive/export/delete) and infrastructure teardown (IaC removal, account/resource cleanup).
6. Plan comms to affected consumers and the verification that confirms safe retirement (no traffic, no live dependency, data archived).
7. Tie the final teardown to the `checklists/decommission-gate.md`.
8. Strip every `<!-- AGENT: ... -->` and `<!-- REPLACE: ... -->` block.
9. Present the draft for review before writing the file.

## Decommission Rules

- Only items with a `retire` disposition in the migration plan belong here — keep/change items are covered by the parity baseline.
- No teardown before the replacing capability has passed the parity gate and consumers have migrated.
- Every retired item has an identified consumer-migration path and a verification step proving nothing live depends on it.
- Data is archived or exported per policy before deletion; teardown removes the IaC so the resource cannot drift back.
- No placeholder template text is allowed in the shipped file.

## Reference Examples

- [`samples/decommission-plan.md`](../../samples/decommission-plan.md)

## Verification

- [ ] File written to `initiatives/<name>/decommission-plan.md`
- [ ] Retirement scope traces to migration-plan `retire` dispositions
- [ ] Consumers/dependencies identified with a migration path each
- [ ] Deprecation timeline, data handling, teardown, comms, and verification documented
- [ ] Decommission gate referenced as the safe-retirement gate
- [ ] No `<!-- AGENT -->` or `<!-- REPLACE -->` text remains
