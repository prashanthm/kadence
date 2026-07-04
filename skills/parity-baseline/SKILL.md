---
name: parity-baseline
description: Author a parity baseline (parity-baseline.md) that turns the AS-IS feature inventory into a no-regression gate with characterization tests. Use to guarantee a brownfield migration loses no functionality.
---

# Parity Baseline Skill

## Purpose

Guarantee "no loss of functionality" across a migration by turning the extracted AS-IS feature inventory into a parity checklist plus a characterization test plan. The parity baseline is the no-regression gate: the migration is not done until every kept/changed AS-IS capability passes on the target.

## When to Use

- After `feature-extraction`, once the AS-IS capability inventory exists
- Alongside `migration-planning`, to define the gate the migration must clear
- Before cutover, to confirm the target matches the source behavior

## Required Inputs

- AS-IS features under `assessments/<system>/features/` (the capability inventory)
- The `migration-plan.md` dispositions (which features are keep/change vs retire)
- The system-overview integration seams and the Evidence Ledger
- Template: [`templates/parity-baseline.md`](../../templates/parity-baseline.md)

## Required Workflow

1. Read [`templates/parity-baseline.md`](../../templates/parity-baseline.md) and treat every `<!-- AGENT: ... -->` block as authoring rules — not text to copy.
2. Build the capability inventory: one row per AS-IS feature with `keep` or `change` disposition (skip `retire` items — those go to the decommission plan).
3. For each capability, define the parity check: the observable behavior that must hold on the target, and how it is verified.
4. Define a characterization test plan: tests written against current AS-IS behavior, run against both source and target to prove equivalence.
5. Capture acceptable deltas explicitly (e.g. a `change` item whose behavior intentionally differs) so they are not flagged as regressions.
6. Express the parity checklist as the gate used at cutover (links to `checklists/parity-gate.md`).
7. Strip every `<!-- AGENT: ... -->` and `<!-- REPLACE: ... -->` block.
8. Present the draft for review before writing the file.

## Parity Rules

- Inventory completeness comes from `feature-extraction` — every kept/changed AS-IS feature must appear; a missing row is an unguarded regression.
- Each parity check is observable and verifiable, not "looks the same".
- Intentional behavior changes are recorded as acceptable deltas with rationale — never silently passed or failed.
- The parity gate must pass before cutover is allowed; tie it to the migration plan's cutover step.
- No placeholder template text is allowed in the shipped file.

## Reference Examples

- [`samples/parity-baseline.md`](../../samples/parity-baseline.md)

## Verification

- [ ] File written to `initiatives/<name>/parity-baseline.md`
- [ ] Capability inventory covers every keep/change AS-IS feature
- [ ] Each capability has an observable parity check and verification method
- [ ] Characterization test plan present; acceptable deltas recorded with rationale
- [ ] Parity gate referenced as the cutover no-regression gate
- [ ] No `<!-- AGENT -->` or `<!-- REPLACE -->` text remains
