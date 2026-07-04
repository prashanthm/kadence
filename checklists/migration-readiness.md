# Migration Readiness Checklist

> Must pass before a migration step's cutover is executed.

## Plan

- [ ] AS-IS -> TO-BE map covers every extracted epic/feature with a disposition (keep/change/add/retire)
- [ ] Migration strategy chosen and justified against the integration seams
- [ ] Work sequenced seam-by-seam; system stays shippable throughout
- [ ] Each migration step has a tested rollback

## Decisions

- [ ] Forward migration ADRs (`Accepted`) supersede the relevant Discovered ADRs, cross-linked
- [ ] Risk register present with mitigations

## Data & Cutover

- [ ] Data migration plan defined (sources, transforms, validation)
- [ ] Cutover procedure documented per step, with rollback triggers
- [ ] Parity baseline referenced as the no-regression gate for this cutover
- [ ] Retired items carried into the decommission plan
