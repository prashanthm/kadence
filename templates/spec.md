<!--
AGENT: Spec — the COMMITTED code-repo artifact for one feature (Spec-Kit style).

It lives in the CODE repo (not in initiatives/) at `specs/<feature-slug>/spec.md`, alongside two siblings:
  - `plan.md`  — files to touch, implementation steps, ADRs applied, edge cases (the HOW).
  - `tasks.md` — granular, parallelizable [P] work units. Each unit carries a `## Loop AC` block of
                 BEHAVIORAL `verify:` commands (tests pass / file exists / lint clean). There is NO
                 file/line-count tripwire — the feature was already right-sized at generation time
                 (see the feature-generation Sizing section); Loop AC verifies behavior, not diff size.

spec.md itself is the WHAT/behavior contract — no file lists, no steps (those go in plan.md).
Identity is the feature's descriptive slug; the folder name IS the slug. The feature is joined to its
GitHub issue by slug + branch, and the code lands via `Closes owner/repo#N` on the PR — no issue number
stored in this file. Dates/progress live on GitHub, not here.

Strip this entire HTML comment when writing outside templates/ — scaffolding only.
-->

# <!-- REPLACE: Feature Name --> — Spec

> **Feature slug:** <!-- REPLACE: <feature-slug> — this folder is specs/<feature-slug>/ -->
> Product doc: <!-- REPLACE: link to the feature markdown in initiatives/.../features/<feature-slug>.md -->
> Siblings: [`plan.md`](./plan.md) (files/steps/ADRs/edge-cases) · [`tasks.md`](./tasks.md) (granular units + Loop AC)

> Joined to its GitHub issue by slug + branch; the implementing PR lands with `Closes owner/repo#N`. No issue number stored in this file.

## Behavior / What

<!-- REPLACE: The observable behavior this feature adds — the contract, not the implementation. -->

## Acceptance Criteria

- [ ] <!-- REPLACE: Verifiable behavioral outcome 1 -->
- [ ] <!-- REPLACE: Verifiable behavioral outcome 2 -->

## Out of Scope

- <!-- REPLACE: What this feature deliberately does NOT do -->

## ADRs Applied

- <!-- REPLACE: ADR-NNN that constrains this feature; full detail/edge-cases go in plan.md -->

## Task Breakdown

> Granular, parallelizable units live in [`tasks.md`](./tasks.md). Each unit has a `## Loop AC` block whose
> BEHAVIORAL `verify:` commands the engineering work loop runs in the worktree; the agent checks `[x]` only
> after a command exits 0. Loop AC assert observable behavior — never diff size — e.g.:
>
> ```
> - [ ] AC-1: the new endpoint returns 200 for a valid request
>   - verify: `python3 scripts/loop_check.py cmd-succeeds "pytest tests/test_endpoint.py -q"`
> - [ ] AC-2: the config file is created
>   - verify: `test -f config/feature.yaml`
> ```
