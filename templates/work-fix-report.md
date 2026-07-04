# Work Fix Report

Goes in the **draft PR body**. One report per work item. End it with a line
`Closes #<feature-issue>` (the feature issue — the build unit; never an epic). It does
nothing while the PR is a draft, but on merge it auto-closes the issue and advances the
board to **Done**. A bare `Refs #N` leaves the issue open and the board card stuck.

> **v2:** the loop delivers **real code work only** — there is no metadata-only
> closeout. `report_gate.py` rejects a report missing the required **Skill used**
> field or naming a non-existent skill, and rejects a report whose claimed changed
> files are not present in `git diff` (diff-vs-claim).

## Work item

| Field | Value |
|-------|-------|
| Work item type | `chore` / `dependabot` / `feature` / `fix` |
| **Skill used** (required) | `<skill slug that implemented this, e.g. implement>` |
| Source issue | `<owner>/<repo>#<number>` — `<title>` |
| Risk tier | `auto` / `assist` |
| Branch | `<type>/<issue#>-<slug>` |

> **Never include local filesystem paths.** The Work Fix Report is published to a
> public PR — do **not** put the operator's clone path, worktree path, home directory,
> username, or any absolute `/Users/...` / `/home/...` path anywhere in this report.
> Use repo-relative paths only (e.g. `scripts/loop_check.py`, not
> `/Users/<name>/projects/.../scripts/loop_check.py`). This is PII and must never be
> committed or posted.

## Loop AC Evidence

Record verify commands **repo-relative** — strip any absolute/toolkit prefix
(`python3 scripts/loop_check.py …`, never `python3 /Users/<name>/…/scripts/loop_check.py`).

| AC | Description | Verify command | Exit code |
|----|-------------|----------------|-----------|
| AC-1 | … | `python3 scripts/loop_check.py …` | 0 |
| AC-2 | … | `…` | 0 |

## Diff summary

| File | Change |
|------|--------|
| `path/to/file` | … |

Every file listed here must appear in the PR's `git diff` (checked by `report_gate.py`).

## Isolation

- **Primary clone untouched:** yes (only `git fetch` in the candidate's clone; all
  edits in the worktree).
- **Draft — operator must mark ready for review.** The loop does not run
  `gh pr ready` or request reviewers.

## AI Attribution

Include the canonical table from `templates/pull-request.md`. Fill **Author** with
the configured agent (`agent_backend` / `agent_model` from config).

| Role | Model | Tool |
|------|-------|------|
| Author | `<agent_model or —>` | `Cursor` / `GitHub Copilot` / `Claude Code` |
| Spec | — | — |
| Reviewer | — | — |

## Human merge

Merge remains **human-owned**. This loop does not merge, approve, or close parent
feature/epic issues.
