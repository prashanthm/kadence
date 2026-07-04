# Release Gate Checklist

> The single, test-evidence-driven gate that promotes an immutable `vX.Y.Z` tag.
> `vX.Y.Z` is the **output** of this gate, not its trigger: the automated suites
> run against the candidate `main-<sha>` digest, and only after R1–R6 is signed is
> that exact digest **crane-copied** to `vX.Y.Z` — never rebuilt. See
> [e10-f01 Release Gate Codification](../../initiatives/ai-native-development/features/e10-f01-release-gate-codification.md).

## Candidate (R1 — scope)

- [ ] Release scope agreed (`release-scope.md`) with the Release AC enumerated
- [ ] Candidate pinned: `release-candidate.json` records the `main-<sha>` tag + **candidate digest** + commit
- [ ] Semver rationale recorded (why this is the next `vX.Y.Z`)

## Test evidence (R2 — keyed to the candidate digest)

> Every suite runs against the **candidate digest** and emits a digest-keyed result
> (`test-evidence.json`). The preflight rejects any suite that ran against a different digest.

- [ ] **Functional** suite passed against the candidate digest
- [ ] **Integration** suite passed against the candidate digest
- [ ] **Regression** suite passed against the candidate digest
- [ ] **E2E** suite passed against the candidate digest
- [ ] **Performance** suite within SLO budget against the candidate digest (or `waived` with a recorded owner)

## Notes & ceremony (R3)

- [ ] Release notes reviewed/approved (`release-notes-<ver>.md`)
- [ ] CHANGELOG diff prepared
- [ ] Doc-update checklist complete (no stale docs reference the prior version)

## Concern review (R4 — release-review-batch)

- [ ] Quality, Security (CVE scan on the candidate digest), Compliance + traceability, Observability, and Release-metadata concerns all returned `PASS`
- [ ] No unresolved Critical/High in any concern (the fan-in is conjunctive — one FAIL fails R4)
- [ ] Full traceability verified: every PR → task → feature → epic

## Governance (R5)

- [ ] Traceability matrix + provenance draft attached
- [ ] SBOM generated for this release
- [ ] Rollback plan documented; monitoring window defined (duration, escalation contact)

## Tag authorization (R6 — the hard block)

- [ ] Dual PO + Builder sign-off recorded (`release-approval-record.md`)
- [ ] `release_tag_preflight.sh` passes against `release-evidence.json` — all suites green vs candidate, R1–R5 passed, **test-evidence digest == candidate digest == digest being promoted**, Release AC complete
- [ ] Tag is **crane-copied** from the validated candidate digest — **no rebuild on tag**
- [ ] Post-promotion smoke confirms the `vX.Y.Z` digest equals the candidate digest
