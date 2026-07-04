---
name: pr-comment-fix-loop
description: Local polling loop for operator-authored PRs with reviewer feedback — fix comments once per PR lifetime in a worktree, post PR Comment Fix Report, re-request reviewers. Human merges. Use with pr-comment-fix-loop.prompt.md and cron wrapper.
---

# PR Comment Fix Loop Skill

## Purpose

Poll GitHub for operator-authored open PRs with ≥2 non-operator review submissions, implement fixes in an **isolated worktree** (primary clone untouched), post **PR Comment Fix Report**, re-request original reviewer(s) when warranted. Runs **once per PR lifetime**. Author-side complement to [pr-review-loop.prompt.md](../../.github/prompts/pr-review-loop.prompt.md).

## When to Use

- Local launchd **every 15 min** (:00/:15/:30/:45); a firing still running when the next tick fires is skipped (single-instance lock)
- After ≥2 reviewers leave feedback on operator's open PR (including APPROVED reviews with Low findings)

## Required Inputs

- Operator overlay: `~/.config/ai-sdlc/pr-comment-fix-loop.yaml` (created by setup script; merged with toolkit `config.example.yaml`)
- `gh` authenticated as operator
- Local CLI login: `agent login` (Cursor) or `copilot login` (Copilot) — see loop-agent-backends.md
- Primary clone path (`git.primary_clone` in overlay)
- Prompt: `.github/prompts/pr-comment-fix-loop.prompt.md`

## Operator setup

See [README.md](README.md) — run `pr-comment-fix-loop-setup.sh install`. Agent backends: [loop-agent-backends.md](../../standard/loop-agent-backends.md).

## Required Workflow

1. Pre-flight: `gh auth status`; `git fetch` in primary clone only.
2. Run `discover_pr_fix_candidates.py`; exit if no candidate.
3. Acquire worktree, fix, verify, commit locally.
4. Write draft report + **firing evidence** under `.sdlc/pr-fix-reports/` on PR branch.
5. **Submit mode** (default: `report.submit: true`): push, post comment, apply labels, re-request per policy.
6. **Draft mode** (`report.submit: false` or `PR_FIX_REPORT_DRAFT=1`): no push/gh until operator runs `pr-comment-fix-loop-publish.sh` with `PR_FIX_PUBLISH=1`.

### Optional / non-blocking follow-ups

See [pr-comment-fix-loop.prompt.md](../../.github/prompts/pr-comment-fix-loop.prompt.md) — **Evaluate findings → Optional / non-blocking follow-ups**. Fix when small and in-scope; defer cross-cutting tooling or blocked work; record every item in the disposition table.

## Scripts

| Script | Role |
|--------|------|
| `discover_pr_fix_candidates.py` | Deterministic discovery + idempotency gates; the returned candidate already carries `comment_inventory` — no separate context-assembly step |
| `pr-comment-fix-loop.sh` | Agent wrapper |
| `pr-comment-fix-loop-setup.sh` | Install cron, config overlay, launchd |
| `pr-comment-fix-loop-cron.sh` | Cron entrypoint (discover → agent → status) |
| `pr_fix_cron.py` | Cron orchestration + label bootstrap |
| `pr_fix_status.py` | Firing status reports (local + PR branch git evidence) |
| `pr-comment-fix-loop-submit.sh` | Prepare publish artifacts (draft mode) |
| `pr-comment-fix-loop-publish.sh` | Human gate (`PR_FIX_PUBLISH=1`) |
| `worktree_acquire.sh` / `worktree_release.sh` | Shared with engineering-work-loop |

## Cron install (macOS launchd)

See [README.md](README.md) — `pr-comment-fix-loop-setup.sh install` (runs **every 15 min**; Mac must be awake).

## Status reports

| Location | Purpose |
|----------|---------|
| `~/.local/share/ai-sdlc/pr-comment-fix-loop-latest.md` | Last firing (any outcome) |
| `~/.local/share/ai-sdlc/pr-comment-fix-loop-firings.log` | JSONL history |
| `.sdlc/pr-fix-reports/<pr>-firing-latest.md` | Git evidence on PR branch |
| `.sdlc/pr-fix-reports/<pr>-firing-<ts>.json` | Machine-readable firing record |

Firing evidence is pushed with the PR branch when operator runs publish.

## Config

- `report.submit` / `report.push` / `report.apply_labels` — default **true** in `config.example.yaml`; set all `false` for draft-only human gate
- `status.latest_json` / `status.latest_md` / `status.firing_log` / `status.firing_dir`
- `labels.*` — bootstrap created on first cron run if missing
- `state_log` — JSON-lines idempotency log (published cycles)

## Never

- Merge PRs
- Checkout/switch primary clone for edits (except `git fetch`)
- Auto-push or auto-post PR comments in draft mode
- React to webhooks — polling only

## Related

- Feature: [e04-f09](../../../initiatives/ai-native-development/features/e04-f09-pr-comment-fix-loop.md)
- Report template: [templates/pr-comment-fix-report.md](../../templates/pr-comment-fix-report.md)
- Worktree pattern: [engineering-work-loop](../engineering-work-loop/SKILL.md)
