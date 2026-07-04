---
name: pr-review-loop
description: Local polling loop for reviewer-side PR review — discover PRs where review is requested of the operator, post one review per PR per HEAD via gh pr review, never merge. Reviewer-side complement to pr-comment-fix-loop. Use with pr-review-loop.prompt.md and cron wrapper.
---

# PR Review Loop Skill

## Purpose

Poll GitHub for open PRs where the operator's review is **requested** (`review-requested:@me`), apply the [pr-review-loop.prompt.md](../../.github/prompts/pr-review-loop.prompt.md) decision matrix, and post **at most one review per PR per HEAD** via `gh pr review`, using the findings-first format in [pr-review.prompt.md](../../.github/prompts/pr-review.prompt.md). **Never merges.** Reviewer-side complement to [pr-comment-fix-loop](../pr-comment-fix-loop/SKILL.md) (author-side) and [engineering-work-loop](../engineering-work-loop/SKILL.md) (assignee-side).

## When to Use

- Local scheduler during work hours (:00/:15/:30/:45 on macOS launchd; every 15 min via Windows Task Scheduler)
- After someone requests the operator's review on a PR

## Key difference from the other two loops

A reviewer **posts a review — it does not edit, commit, or push code.** So there is **no worktree** in the common path. Context comes from `gh pr diff` + `gh pr view --json` (intent / prior rounds / CI) + targeted reads of surrounding files from the operator's base clone. A **read-only** worktree is materialized **only** when the PR modifies `` itself.

## Required Inputs

- Config: `config.example.yaml` (operator overlay via `pr-review-loop-setup.sh install`)
- `gh` authenticated as the acting reviewer
- Base clone (`git.primary_clone`) for cross-file context + optional toolkit worktree
- Prompt: `.github/prompts/pr-review-loop.prompt.md`

## Required Workflow

1. **Cron preflight:** `gh auth status`; single-instance lock.
2. **Discovery:** `discover_pr_review_candidates.py` lists `review-requested:@me` PRs across the configured repos and applies the decision matrix.
3. **Skip** (deterministic, in discovery): draft, self-PR, operator already APPROVED at HEAD, CHANGES_REQUESTED without re-request, already reviewed this HEAD (idempotency), adjacent-reviewer-at-HEAD, not-requested.
4. **Agent (per eligible PR):** for **each** eligible PR the firing reviews, gather context via `gh pr diff` / `gh pr view --json` (read-only worktree only for toolkit PRs). A firing reviews every eligible PR across all configured repos, one focused agent run per PR; a per-PR failure is isolated and the firing continues.
5. **Post one review per PR** via `gh pr review` (approve / request-changes / comment) with the findings-first format. Findings continuity + head-SHA citation per the Loop Discipline. Still **at most one review per PR per HEAD**.
6. **Labels (rollup telemetry):** cron sets `pr-review-loop-in-progress` before the agent run and `pr-review-loop-complete` after GitHub verifies the operator review at HEAD (`report.apply_labels`, default true). Counted in weekly `scorecard.json` → `loop_signals.pr_review` and portfolio rollup.
7. **Cron status:** record the firing in the JSONL firing log — one row per reviewed PR (`review_posted` / `agent_error`), plus a `review_posted` row appended to `state_log` per posted review so the next firing skips already-reviewed HEADs. Firing outcome is `review_posted` (all ok), `partial` (some errors), `no_work`, or `agent_error`.

## Decision matrix

See [pr-review-loop.prompt.md](../../.github/prompts/pr-review-loop.prompt.md). Idempotent per `owner/repo#pr@headRefOid` — re-reviews only when HEAD advances **and** the operator is re-added to `reviewRequests`.

## Scripts

| Script | Role |
|--------|------|
| `pr-review-loop-setup.sh` | **Install / run / status** (start here) |
| `pr-review-loop-cron.sh` | Scheduled entrypoint (single-instance lock) |
| `pr_review_loop_cron.py` | Orchestrator: discover → agent (backend fallback) → labels → status |
| `discover_pr_review_candidates.py` | `review-requested:@me` discovery + decision-matrix gates |
| `pr-review-loop.sh` / `invoke_loop_agent.sh` | Agent run wrapper / backend dispatcher |

## Never

- Merge PRs, approve on the author's behalf, or run `gh pr ready`
- Edit / commit / push code (reviewer posts a review only)
- Re-review the same HEAD, or re-review after CHANGES_REQUESTED without an explicit re-request
- Review self-authored PRs
- React to webhooks — polling only

## Related

- Feature: [e04-f06](../../../initiatives/ai-native-development/features/e04-f06-pr-review-monitor.md)
- Review format: [pr-review.prompt.md](../../.github/prompts/pr-review.prompt.md)
- Agent backends: [standard/loop-agent-backends.md](../../standard/loop-agent-backends.md)
