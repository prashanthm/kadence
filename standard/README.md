# The Standard (v2, lean)

The lifecycle definition. v2 is a deliberate reduction from the accreted v1 — three
durable layers, one committed spec folder per feature, and status/dates in GitHub.

## Layers (three, not five)

| Layer | Home | Holds |
|-------|------|-------|
| **Initiative** | `initiatives/<slug>/` | Why the program exists; funding/scope (PM) |
| **Epic** | `initiatives/<slug>/epics/` | A capability area; maps to a GitHub milestone/phase (PM) |
| **Feature** | `initiatives/<slug>/features/` | **The build unit.** What / Why / Acceptance Criteria. One feature → one PR → `Closes #` |

Engineering detail lives in the **code repo**, not the product docs:

```
<code-repo>/specs/<feature-slug>/
  spec.md    what/AC restated for engineers + design
  plan.md    files · steps · ADRs applied · edge cases
  tasks.md   granular, [P]-parallel implementation STEPS; each carries a
             behavioral Loop AC (verify: commands — tests pass / file exists /
             lint clean). No diff-size tripwire; size is never a gate.
```

**Task** is not a standard layer — it is the ordered/`[P]` step breakdown *inside* one
already-right-sized feature. Feature sizing is decided at generation (one coherent,
PR-sized increment); a big capability becomes several features with a `Depends On` graph.

## Identity, ordering, scheduling

- **Identity** = a descriptive **slug** (no positional `eNN-fNN` IDs).
- **Order** = issue dependencies (`blocked by`) + the `Ready for Dev` gate.
- **Date** = a GitHub Projects target-date + Roadmap view (cross-repo); milestone `due_on` (per-repo).
- **Proof** = a Release + tag.

## Durable vs mutable

- **Durable (markdown, forever):** initiative · product brief (Epic Index = release order by phase
  name) · epics · features · ADRs · `specs/<feature>/`. No status, dates, or IDs.
- **Mutable (GitHub, live):** status · dates & progress · what shipped.
- **The join:** slug + branch + `Closes owner/repo#N`; the issue links out to the doc + spec.

There is no `roadmap.md`. A schedule changes, so it lives in GitHub.

## The enforcement principle

**The agent proposes; the deterministic harness disposes.** `kadence doctor` gates every change; the
loop re-runs every `verify:` itself; a green acceptance criterion requires an exit-0 command, never an
agent's self-check. Metadata-only outcomes do not count as delivered work.

> Full rationale and the v1→v2 change-list: `assessments/kadence-v2` in product-workspace.
