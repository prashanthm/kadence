# Parity Gate Checklist

> No-regression gate. Must pass before a cutover switches a tenant/seam from source to target.

## Coverage

- [ ] Every keep/change AS-IS feature appears in the parity baseline capability inventory
- [ ] Each capability has an observable, verifiable parity check
- [ ] No AS-IS feature is silently dropped (retired items are in the decommission plan, not here)

## Verification

- [ ] Characterization tests run against both source and target
- [ ] All keep/change parity checks pass on the target
- [ ] Acceptable deltas confirmed intentional, with rationale recorded
- [ ] Any failing check blocks cutover (rollback, fix, re-run)
