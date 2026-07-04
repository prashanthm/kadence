---
name: pr-traceability
description: PR-time traceability + compliance review — links PR to feature/epic/ADRs, checks license headers, signed commits, SBOM readiness. Read-only; runs on the diff. Merges the old traceability-verify + compliance-review (the markdown-status/M18 half is gone in v2).
---

# PR Traceability Skill

## Purpose

At PR time, verify the change is **traceable** (it maps to a feature and honors its ADRs)
and **compliant** (license headers, signed commits, SBOM readiness). This merges the v1
`traceability-verify` and `compliance-review` skills. In v2 there is **no markdown-status /
M18 drift check** — status lives in GitHub, so there is no drift to review. The reviewable
artifact is the **PR diff**.

## When to Use

- On an open PR, as part of the review batch (alongside `security-review`, `quality-review`,
  `observability-review`).
- Before a release, to confirm the traceability chain is complete for the scope.

## Inputs

- The PR (description, commits, changed files, `Closes owner/repo#N`).
- The linked **Feature** doc (`initiatives/<slug>/features/<feature-slug>.md`) and its `Part of
  epic:` link, plus any ADRs the feature or its `specs/<feature>/` reference.
- The org license policy (a license ADR, if present).

## Required Workflow

1. **Resolve the chain from the PR.** Read the PR's `Closes owner/repo#N` → the Feature issue
   → its doc (by slug) → its epic (via `Part of epic:` link) → ADRs listed in the feature /
   the code-repo `specs/<feature>/`. The join is the issue + slug, not a stored number.
2. **Build the traceability matrix.** One row per acceptance criterion / requirement:

   | Requirement | Source (Feature AC / Epic / ADR) | PR Evidence (file/test/commit) | Met / Partial / Missing |
   |-------------|----------------------------------|--------------------------------|-------------------------|

   Every feature acceptance criterion must map to concrete PR evidence (a changed file, a test,
   a commit). Flag any `Partial` / `Missing`.
3. **License headers.** New source files carry the required license header per the license ADR.
4. **Signed commits.** If the repo requires signing, every commit in the PR is signed.
5. **SBOM readiness.** New third-party dependencies are declared where the repo expects them
   (lockfile / manifest); flag undeclared additions.
6. **ADR conformance.** The change does not violate an `Accepted` ADR that `Applies To` it; if
   it does, the PR needs a superseding ADR first.

## Output

A read-only review comment: the traceability matrix + a compliance checklist
(license / signed-commits / SBOM / ADR-conformance), each Pass / Fail / N-A with the gap
listed. **This skill never edits code, never merges, and never sets status** — it reports.

## Not in scope (v2)

- **No markdown `**Status:**` drift check** — status is the GitHub issue/board's job.
- **No M18 / gh_ahead / epic_milestone / compliance-closeout** — those are removed in v2.
- **No task layer** by default — the chain is Feature → Epic; a `tasks.md` unit is traced to
  its parent feature only when a feature was decomposed.

## Related

- Runs alongside: [`security-review`](../security-review/SKILL.md),
  [`quality-review`](../quality-review/SKILL.md),
  [`observability-review`](../observability-review/SKILL.md).
- The PR is the reviewable artifact — see [`pr-review`](../pr-review/SKILL.md).
