---
name: migration-planning
description: Author a migration plan (migration-plan.md) that maps the AS-IS reference model to the target state as a delta, with strategy, sequencing, cutover, and rollback. Use to plan a brownfield re-platform once the AS-IS baseline exists.
---

# Migration Planning Skill

## Purpose

Turn the AS-IS reference model and the target initiative into an executable migration plan: an AS-IS -> TO-BE mapping keyed to extracted epics/features and discovered ADRs, with a migration strategy, sequencing, data migration, cutover, and rollback. The plan expresses the future as a **delta** against the recovered past — keep / change / add / retire — not a from-scratch build.

## When to Use

- After the AS-IS reference model exists and the forward `initiative.md` / `product-brief.md` are drafted
- Planning a re-platform, dependency swap, or strangler-fig replacement of an existing system
- Refreshing a migration plan after the target architecture changes

## Required Inputs

- AS-IS reference model: `assessments/<system>/system-overview.md`, `epics/`, `features/`, `adrs/` (Discovered)
- Forward initiative context: `initiatives/<name>/initiative.md` and `product-brief.md`
- Migration ADRs (Accepted) that supersede discovered ADRs, via `adr-maintenance`
- Template: [`templates/migration-plan.md`](../../templates/migration-plan.md)

## Required Workflow

1. Read [`templates/migration-plan.md`](../../templates/migration-plan.md) and treat every `<!-- AGENT: ... -->` block as authoring rules — not text to copy.
2. Read the AS-IS model and the forward initiative/brief.
3. Build the AS-IS -> TO-BE map: one row per extracted epic/feature with a disposition (`keep` / `change` / `add` / `retire`) and the target it maps to.
4. State the migration strategy (strangler-fig / parallel-run / big-bang cutover) and why, referencing the integration seams from the system-overview.
5. Sequence the work seam-by-seam: which seam is swapped first, dependencies, and the order that keeps the system shippable throughout.
6. Plan data migration (sources, transforms, validation) and the cutover + rollback procedure for each step.
7. Build the risk register; link each discovered ADR being superseded to the migration ADR that replaces it.
8. Reference the `parity-baseline.md` as the no-regression gate and the `decommission-plan.md` for retired items.
9. Strip every `<!-- AGENT: ... -->` and `<!-- REPLACE: ... -->` block.
10. Present the draft for review before writing the file.

## Migration Rules

- Every TO-BE item traces to an AS-IS epic/feature disposition — no orphan target work, no silently dropped capability.
- `retire` dispositions must be carried into the decommission plan; `keep`/`change` must be covered by the parity baseline.
- Each migration step has a rollback; a step without a tested rollback is not ready.
- Migration ADRs supersede discovered ADRs explicitly (managed via `adr-maintenance`).
- Phasing intent lives here; execution tracking lives in GitHub.
- No placeholder template text is allowed in the shipped file.

## Reference Examples

- [`samples/migration-plan.md`](../../samples/migration-plan.md)

## Verification

- [ ] File written to `initiatives/<name>/migration-plan.md`
- [ ] AS-IS -> TO-BE map present with a disposition per extracted epic/feature
- [ ] Strategy, seam sequencing, data migration, cutover, and rollback documented
- [ ] Risk register present; superseded discovered ADRs linked to migration ADRs
- [ ] Parity baseline and decommission plan referenced
- [ ] No `<!-- AGENT -->` or `<!-- REPLACE -->` text remains
