# PR Comment Fix Report

Post as a **PR issue comment** after a successful fix cycle. One report per PR lifetime.

## Trigger

| Field | Value |
|-------|-------|
| PR | `#<number>` — `<title>` |
| Head SHA at start | `<7-char sha>` |
| Automated feedback count | `<n>` items from configured actors |

## Disposition table

| Source id | Finding (summary) | Disposition | Fix commit / file | Notes |
|-----------|-------------------|-------------|-------------------|-------|
| review `<id>` | H1: … | Fixed | `<sha>` / `path` | |
| review `<id>` | L2: … | Deferred | — | rationale |
| issue_comment `<id>` | … | No-change | — | already addressed |

## Fix Cross-check Matrix

| Finding | Requirement / AC | Addressed in diff? | Verified? |
|---------|------------------|--------------------|-----------|
| H1 | AC-3: … | yes — `file:line` | `pytest …` exit 0 |
| L2 | — | deferred | n/a |

## Verification

| Command | Exit code |
|---------|-----------|
| `verify: …` | 0 |
| `pytest …` | 0 |

## Re-request

Follow **Re-review policy** in the prompt. Either list reviewers or state `skipped — <reason>`.

```json pr-fix-rereview
{"required": false, "reason": "approved_no_critical_high_fixes", "all_reviews_approved": true, "fixed_severities": [], "reviewers": []}
```

## AI Attribution

Include the canonical table from `templates/pull-request.md`. Fill **Author** with the configured fix agent (`agent_backend` / `agent_model` from config).

| Role | Model | Tool |
|------|-------|------|
| Author | `<agent_model or —>` | `Claude Code` |
| Spec | — | — |
| Reviewer | — | — |

## Idempotency

Fix cycle: **complete** (will not auto-run again on this PR).

Labels applied: `pr-fix-cycle-complete`; `pr-fix-cycle-in-progress` removed.

## Human merge

Merge remains **human-owned**. This loop does not merge, approve, or mark the PR ready.
