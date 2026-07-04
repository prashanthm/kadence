# Decommission Gate Checklist

> Safe-retirement gate. Must pass before tearing down a retired system/component.

## Preconditions

- [ ] Replacing capability has passed the parity gate
- [ ] All consumers/dependencies migrated off the retired item
- [ ] Retirement scope traces to migration-plan `retire` dispositions

## Data & Teardown

- [ ] Data archived or exported per retention policy; archive integrity verified
- [ ] Infrastructure teardown removes the IaC so resources cannot drift back
- [ ] Retired code paths removed

## Verification

- [ ] No live traffic to the retired item during the monitoring window
- [ ] No live dependency remaining (confirmed via graphify / dependency scan)
- [ ] Comms sent to affected consumers
