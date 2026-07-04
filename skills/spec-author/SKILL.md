---
name: spec-author
description: Author ONLY the code-repo specs/<slug>/{spec,plan,tasks}.md trio for a feature (no production code) on a spec/<n>-<slug> branch, and open a spec-only draft PR for engineer review. Used by the spec-loop (Ready for Spec gate), before implement-loop writes code.
---

# Spec Author Skill

## Purpose

Turn a feature's **intent** (What / Why / Acceptance Criteria / `Part of epic:`) into the committed
engineering spec — the `specs/<slug>/` trio in the code repo — **without writing any production code**.
This is the deliberate "engineers review the plan before the agent builds it" step: the agent drafts the
spec, opens a **spec-only draft PR**, and stops. An engineer reviews and merges that PR; the merge moves
the board card to `Ready for Dev`, where [`implement`](../implement/SKILL.md) (run by implement-loop) writes
code strictly to the approved spec.

`spec-author` (run by **spec-loop**) writes the plan; `implement` (run by **implement-loop**) writes the
code. Splitting them gives engineers a plan-review gate while agents still do the drafting and building.

## When to Use

- The feature's board card is in **`Ready for Spec`** (the spec-loop's Status gate).
- No approved `specs/<slug>/` exists yet, or it needs (re)drafting for review.
- Branch follows `spec/<issue-number>-<slug>` convention.

## Required Inputs

- Feature markdown path (`initiatives/<slug>/features/<file>.md`) or the GitHub issue number.
- The parent initiative's `INDEX.md` (`initiatives/<slug>/INDEX.md`, in product-workspace even though the
  working directory is the code repo) — the required duplication-check fast path; see workflow step 2a
  below.
- Relevant ADRs (the feature's `Depends On` + epic cross-cutting ADRs).
- The code repo as working directory (the spec lands here, not in `initiatives/`).

## Required Workflow

0. **Branch setup** — sync the base ref, create the spec branch `spec/<issue#>-<slug>`.
1. **Read the feature md** — What, Why, Acceptance Criteria, Depends On, `Part of epic:`.
2. **Confirm Depends On** — if an upstream feature or a required ADR is not satisfied/Accepted, **block**
   and report it rather than drafting a spec on an unratified foundation.
2a. **Required — read `INDEX.md` before drafting.** Read the parent initiative's `INDEX.md`
    (`initiatives/<slug>/INDEX.md`) and scan its Features table for a row — other than the feature being
    specced — whose scope appears to already cover the behavior about to be specified. If `INDEX.md` does
    not exist yet for this initiative (bootstrap case, INDEX.md not found), **proceed with a noted caveat**
    ("`INDEX.md` not found — proceeding without an index-based duplication check") rather than failing or
    blocking. If an existing row appears to overlap, **stop and present that match** (slug, scope, doc
    path) to the user/agent for confirmation **before** authoring the spec trio — do not silently proceed
    past an apparent match.
3. **Author the trio** in `specs/<slug>/` (and NOTHING else — no `src/` changes):
   - `spec.md` — the behavior/AC contract for engineers (the WHAT). No file lists, no steps.
   - `plan.md` — files to touch, implementation steps, ADRs applied, edge cases (the HOW).
   - `tasks.md` — the ordered/`[P]` implementation-step units, **each carrying a `## Loop AC` block of
     BEHAVIORAL `verify:` commands** (tests pass / file exists / lint clean). No diff-size tripwire.
4. **Self-check** — every AC in the feature maps to a task + a behavioral Loop AC; the plan honors every
   `Depends On` ADR; the files list is a real scope contract; no production code was written.
5. **Commit and push** — stage **only** `specs/<slug>/**`; commit on the `spec/<n>-<slug>` branch.
6. **Open a spec-only draft PR** — title `Spec: <slug>`; body summarizes the plan + links the feature doc
   and issue. **The PR references the feature issue with `Refs #<feature-issue>` — NOT `Closes`.** The
   feature issue must stay OPEN for the build phase; only implement-loop's code PR will `Closes` it.
7. **Return payload** — spec files written, branch, PR URL.

## What this skill must NOT do

- **No production code.** Touch only `specs/<slug>/**`. If you find yourself editing `src/`, stop —
  that's implement-loop's job.
- **No `Closes #<feature-issue>`.** A spec PR that closed the feature issue would remove it from the
  board before any code exists. Use `Refs #<feature-issue>`.
- **No merge, no board move.** The engineer merges the spec PR; a merged `spec/*` PR auto-moves the card
  `Ready for Spec → Ready for Dev` via `project-status-on-pr.yml`. This skill only opens the draft.

## Git workflow

- Branch: `spec/<issue#>-<slug>` (the `spec/` prefix is what the board automation keys on to move the
  card to `Ready for Dev` on merge — keep it exactly).
- Base ref: `main` by default; the loop forks from `ENGINEERING_LOOP_BASE_REF` (e.g. an integration branch).
- Stage only `specs/<slug>/**`.

## The two-loop flow (context)

```
Ready for Spec  → spec-loop → spec-author → spec/<n>-<slug> PR (draft, Refs #issue)
     ↑ human moves here (or the card starts here)      │ engineer reviews + merges
                                                        ▼
Ready for Dev   ← (auto on spec-PR merge, project-status-on-pr.yml)
     │ implement-loop → implement → feat/<n>-<slug> PR (draft, Closes #issue)
     ▼
In review → Done
```

## Verification

- [ ] `INDEX.md` read (or its absence noted as a caveat) before authoring the spec trio; any apparent
      existing-feature match was surfaced to the user/agent for confirmation before drafting
- [ ] `specs/<slug>/{spec,plan,tasks}.md` all present; every feature AC maps to a task + behavioral Loop AC
- [ ] `tasks.md` Loop AC are behavioral only (no diff-size tripwire)
- [ ] Only `specs/<slug>/**` changed — no production code
- [ ] Branch is `spec/<issue#>-<slug>`; PR is draft and uses `Refs #<feature-issue>` (never `Closes`)
- [ ] Every `Depends On` ADR is Accepted; blockers reported rather than specced over
