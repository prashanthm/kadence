---
name: implement
description: Implement production code for a feature from its intent doc plus the code-repo specs/<feature>/ folder (spec, plan, tasks) on a feature branch. Absorbs spec-driven implementation — reads specs/<feature>/{spec,plan,tasks}.md. Use for the build cycle (Feature → PR).
---

# Implement Skill

## Purpose

Write production code that satisfies a feature's Acceptance Criteria. The feature doc holds **intent** (What / Why / AC / `Part of epic:`); the *how* lives in the code repo's `specs/<feature>/` folder. This skill reads both, then implements on a feature branch.

It **absorbs spec-driven implementation** and **authors the spec trio at build time**: create/read `specs/<feature>/spec.md` (behavior + AC), `plan.md` (files, steps, ADRs, edge cases), and `tasks.md` (the granular implementation-step units, each with a behavioral `## Loop AC` block) and implement strictly to them. The feature was already right-sized at generation (one coherent, PR-sized increment), so this is the step breakdown *within* one feature — never a step to split the feature.

## When to Use

- Feature is ready to build and a human has cleared it on the GitHub board (`Ready for Dev`). When the engineering work loop is Status-gated, it implements **only** items in that Status.
- Branch follows `feat/<issue-number>-<slug>` convention
- Single-repo work that lands as one PR — the feature was already sized to one coherent, PR-sized increment at generation time (see [`feature-generation`](../feature-generation/SKILL.md) Sizing)

## Required Inputs

- Feature markdown path (e.g. `initiatives/<slug>/features/<file>.md`) or GitHub issue number
- The code repo's `specs/<feature>/` folder: `spec.md`, `plan.md`, and (when decomposed) `tasks.md`
- Feature branch (create if missing: `feat/<issue#>-<slug>`)
- Repo root as working directory

## Required Workflow

0. **Branch setup** — sync `main`, create feature branch (see [Git workflow](#git-workflow) below).
1. **Read feature md** — What, Why, Acceptance Criteria, Depends On, `Part of epic:`.
2. **Read `specs/<feature>/`** — `spec.md` (Files + Steps + scope contract), `plan.md`, and `tasks.md` if present. The spec Files list is the scope contract.
3. **Confirm Depends On** — block if upstream features or ADRs are not satisfied; report blockers.
4. **If no spec exists and work is non-trivial** — draft `specs/<feature>/spec.md` (Files, Steps, Verification) and present it before implementing.
5. **Run a live grep/search before writing new code — required, not optional.** For each behavior/symbol/module the spec's Files/Steps are about to introduce — or, when no spec exists, the feature AC/What — search the target repo's **current working tree** (`grep`/`rg`/`git grep`/glob, or the agent's native code-search tool — whatever's available; no exact symbol name yet is not an exemption, search on the closest available terms) for an existing implementation that already covers it. This search is **live** — executed against the working tree fresh, every run — and is **independent of, not backed by, and not satisfied by consulting `INDEX.md`**: `INDEX.md` is a planning-layer, epic/feature-scale artifact (used by [`feature-generation`](../feature-generation/SKILL.md), [`epic-generation`](../epic-generation/SKILL.md), and [`spec-author`](../spec-author/SKILL.md)) that goes stale between commits; this step is a code-scale, this-instant check, and doing one never exempts the other. **If the search finds an existing implementation that already covers the requested behavior, stop and present that match (file path + matching symbol) before writing anything new** — do not silently proceed to write a duplicate.
6. **Execute in order** — follow `tasks.md` units (respect dependency/`[P]` ordering) or `spec.md` steps; implement only files listed in the spec's Files section.
7. **Implement scope only** — touch files in the spec Files list or implied by the feature AC; no feature creep.
8. **Check AC** — mark `- [x]` only when verifiably met; never check AC speculatively.
9. **Verify** — run commands from the spec/plan Verification section or derive from AC.
10. **Commit and push** — stage only in-scope files; commit and push the feature branch (see [Git workflow](#git-workflow)).
11. **Open PR** — human confirms; use the PR template with AI Attribution; `Closes #<feature-issue>` only when all AC are `[x]`.
12. **Return payload** — changed files, branch, verification results, PR URL if opened.

## Git workflow

Derive branch name from the feature md header and slug:

- Issue number: `**GitHub Issue:** [#N](...)` (on the issue, not the doc) or the passed issue number
- Slug: the feature's descriptive slug
- Branch: `feat/<N>-<slug>`

**Start work** (from repo root):

```bash
git fetch origin
git checkout main
git pull origin main
git checkout -b feat/<N>-<slug>
```

**Commit** (after verification passes; link the feature issue in the message):

```bash
git add <paths-from-spec-Files>
git commit -m "$(cat <<'EOF'
feat(<feature-slug>): short description

One-line why. Closes #<N> when all AC are met.
EOF
)"
```

Use `Refs #<N>` in the commit or PR body for partial work. Do not use `Closes #N` until all Acceptance Criteria are `[x]`.

**Push and open PR** (human gate on PR body):

```bash
git push -u origin HEAD
gh pr create --title "feat(<feature-slug>): short description" --body-file /path/to/pr-body.md
```

Include AI Attribution (Role | Model | Tool). No token counts.

**After merge** — sync local main:

```bash
git checkout main
git pull origin main
```

### Loop mode (engineering work loop)

When invoked from the engineering work loop, run all git commands in `$LOOP_CWD` (worktree path from `worktree_acquire.sh`), **not** the operator's primary clone. Primary clone may only receive `git fetch`. See [engineering-work-loop](../engineering-work-loop/SKILL.md).

## Rules

- **Spec is the scope contract** — implement only files in `specs/<feature>/spec.md` Files (or the feature AC when no spec exists); no scope creep.
- **Closure semantics** — PR body uses `Closes #<feature-issue>` only when **all** Acceptance Criteria are `[x]`. Use `Refs #N` for partial work.
- **No merge to main** — human merges after review.
- Link the feature issue in commit messages when committing.
- Status lives on the GitHub board — do not write or sync a Status field into markdown.

## If a feature turns out too big

Sizing is decided at **generation** ([`feature-generation`](../feature-generation/SKILL.md) Sizing) —
each feature is meant to be one coherent, PR-sized increment. If, while building, you find the feature
genuinely spans two or more independent behaviors / disjoint code paths (would need parallel worktrees or
a multi-PR release), **stop and flag it** so it can be re-generated as multiple right-sized features with
a `Depends On` graph — do not ship an oversized diff. This is a generation-time reshape, not a build-time
split. Within a single right-sized feature, `tasks.md` is just the ordered/`[P]` step breakdown.

## Verification

- [ ] `specs/<feature>/` read (spec/plan/tasks) or a spec drafted for non-trivial work
- [ ] Live grep/search run over the working tree for each behavior/symbol about to be introduced, before writing new code; any existing match surfaced and confirmed, not silently duplicated
- [ ] All spec Files / tasks addressed or explicitly deferred with human approval
- [ ] All AC checked only when verifiably met
- [ ] No out-of-scope changes
- [ ] Branch created from the base ref (default `main`; the loop forks from `ENGINEERING_LOOP_BASE_REF`, e.g. the integration branch) using `feat/<issue#>-<slug>` convention
- [ ] Commit and push on feature branch before PR (human opens PR)
- [ ] No Status field written or synced into markdown
