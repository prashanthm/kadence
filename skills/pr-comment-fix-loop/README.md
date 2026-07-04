# PR Comment Fix Loop — Operator Guide

Automation entry: [scripts/loop-automation.md](../../scripts/loop-automation.md)

Runnable local loop: discover operator PRs with reviewer feedback, fix in a worktree, post PR Comment Fix Report, re-request reviewers when warranted. Human merges.

Agent workflow rules: [SKILL.md](SKILL.md). Fix agent backends: [loop-agent-backends.md](../../standard/loop-agent-backends.md).

## Prerequisites

- `gh auth login`
- **Claude:** `claude auth login` (stored session) or `claude setup-token` (sets `CLAUDE_CODE_OAUTH_TOKEN` for headless) — the only backend
- Git primary clone (auto-detected on install)

See [loop-agent-backends.md](../../standard/loop-agent-backends.md) for install links.

## Run every 15 minutes (macOS)

```bash
scripts/pr-comment-fix-loop-setup.sh install
scripts/pr-comment-fix-loop-setup.sh run
scripts/pr-comment-fix-loop-setup.sh status
```

`install` checks CLI login, creates local dirs, writes operator config overlay (merged with toolkit defaults), installs launchd **every 15 min** (:00/:15/:30/:45), and runs one smoke firing. Each successful run **pushes fixes, posts the PR comment, applies labels, and re-requests reviewers** when configured (default). Mac must be awake and you logged in for scheduled runs. A firing still in progress when the next tick arrives is **skipped** (single-instance lock at `~/.local/share/kadence/pr-comment-fix-loop.lock`), so slow firings never stack.

To pick up new defaults from the toolkit without losing your overrides:

```bash
scripts/pr-comment-fix-loop-setup.sh install --refresh-config --skip-launchd --skip-smoke
```

To reset a bloated overlay back to the minimal operator file, delete `~/.config/kadence/pr-comment-fix-loop.yaml` and re-run `install`.

Manual agent run (outside cron):

```bash
scripts/pr-comment-fix-loop.sh
```

## Where files live

| Path | Location | In git? | Purpose |
|------|----------|---------|---------|
| `~/.config/kadence/pr-comment-fix-loop.yaml` | Your machine | No | Operator overlay (`github_user`, `primary_clone`, `agent_backend`) |
| `~/.local/share/kadence/` | Your machine | No | Worktrees, draft reports, status logs, cron log |
| `.sdlc/pr-fix-reports/` | Repo / PR branch | Yes | Firing evidence after publish |

Toolkit defaults (versioned, auto-merged): `skills/pr-comment-fix-loop/config.example.yaml`

## Config highlights

| Key | Purpose |
|-----|---------|
| `agent_backend` | `claude` (the only backend) |
| `agent_model` | Optional model for AI Attribution Author row |
| `report.submit/push/apply_labels` | Default `true` — full publish at end of run; set `false` for draft-only |
| `min_reviewer_feedback` | Threshold (default 2 non-operator reviews) |

## What each run does

1. Discover eligible PR → fix in worktree → write report
2. **Publish** (default): `git push`, `gh pr comment`, labels, re-request reviewers when warranted
3. Status: `pr-comment-fix-loop-setup.sh status`

## Draft-only mode (optional)

Set in operator overlay:

```yaml
report:
  submit: false
  push: false
  apply_labels: false
```

Then review artifacts under `~/.local/share/kadence/pr-fix-reports/` and publish manually:

```bash
PR_FIX_PUBLISH=1 scripts/pr-comment-fix-loop-publish.sh <pr>
```

## Scripts

| Script | Role |
|--------|------|
| `pr-comment-fix-loop-setup.sh` | **Install / run / status** (start here) |
| `pr-comment-fix-loop-cron.sh` | Scheduled entrypoint (called by launchd) |
| `pr-comment-fix-loop.sh` | Manual agent run |
| `invoke_loop_agent.sh` | Claude Code dispatcher |
| `pr-comment-fix-loop-submit.sh` | Prepare or publish report |
| `pr-comment-fix-loop-publish.sh` | Manual publish gate (`PR_FIX_PUBLISH=1`, draft mode) |
