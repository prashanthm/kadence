# Feature Readiness Checklist

> The single gate before the loop implements a feature: moving its card to **Ready for Dev**.

## Build model (v2)

The Feature is **the build unit** — one feature → one PR → `Closes #`. There is one gate:
**Ready for Dev**. Engineering detail (files/steps/edge-cases) is authored by the loop into
the code repo's `specs/<feature-slug>/` folder at build time — it is **not** required before
the gate, and there is no separate `Ready for Spec` / `Approved` gate.

Feature **sizing is decided at generation** — `feature-generation` emits each feature as one
coherent, PR-sized increment (a big capability becomes several features with a `Depends On`
graph). At build time the loop authors `specs/<feature-slug>/tasks.md` as the ordered/`[P]`
step breakdown *within* that one right-sized feature. There is no build-time split step and no
file/line-count tripwire — Loop AC verifies behavior, not diff size.

## Tier 2 ADRs (first feature only)

- [ ] Testing strategy — unit / integration / e2e defined
- [ ] Observability — logging, tracing, alerting standards accepted
- [ ] Secret management — storage, rotation, access policy accepted
- [ ] Error handling — error format, retry policy accepted
- [ ] License policy — approved licenses, CI enforcement accepted

## Ready for Dev — the gate

- [ ] Feature linked to its parent epic (markdown `Part of epic:` link; GitHub sub-issue relation)
- [ ] Acceptance criteria defined and **verifiable** (each maps to an observable check)
- [ ] Dependencies identified (other features, ADRs, infrastructure) in `Depends On`
- [ ] Test approach defined for every acceptance criterion
- [ ] Applicable ADRs listed (the code-repo `specs/<feature>/` must honor them)
- [ ] The feature is sized to plausibly land as one reviewable PR (if not, re-generate it as several right-sized features with a `Depends On` graph)
- [ ] A human has reviewed the feature and moved its card to **Ready for Dev**
