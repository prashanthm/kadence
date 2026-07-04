# PR Review Loop — Operator Guide

Automation entry: [scripts/loop-automation.md](../../scripts/loop-automation.md)

Runnable local loop: discover PRs where your review is requested, post one review per PR per HEAD, never merge.

Agent workflow: [SKILL.md](SKILL.md). Backends: [loop-agent-backends.md](../../standard/loop-agent-backends.md).

## Prerequisites

- `gh auth login` (as the acting reviewer)
- **Cursor:** `agent login` (default), **Copilot:** `copilot login`, or **Claude:** `claude setup-token` — set `agent_backend` in the overlay
- A base clone (`git.primary_clone`) for cross-file context + the optional read-only toolkit worktree

## Run every 15 minutes (macOS / Windows)

```bash
scripts/pr-review-loop-setup.sh install
scripts/pr-review-loop-setup.sh run
scripts/pr-review-loop-setup.sh status
```

`install` checks CLI login, writes the operator config overlay, installs a scheduler **every 15 min**, and runs one smoke firing. On macOS it installs launchd at `:00/:15/:30/:45`; on Windows it creates a Task Scheduler job named `ai-sdlc-pr-review-loop` that runs every 15 minutes from install time through Git Bash (firings may not align to quarter-hour marks the way launchd does). A firing still in progress when the next tick arrives is **skipped** (single-instance lock at `~/.local/share/ai-sdlc/pr-review-loop.lock`).

On Windows, run the same setup entrypoint from Git Bash:

```bash
scripts/pr-review-loop-setup.sh install
```

The setup wrapper resolves `python3`, `python`, or `py -3`, then the installer creates the scheduled task and points it at `pr-review-loop-cron.sh` via Git Bash. If Git Bash is not on `PATH`, set `BASH_EXE` to your `bash.exe` path before running install.

## Stop the Loop

Use `uninstall` to remove the scheduler entry when you want to stop the loop:

```bash
scripts/pr-review-loop-setup.sh uninstall
```

## No worktree (the key difference)

A review **posts a review — it doesn't edit code**, so there is no worktree in the common path. Context is `gh pr diff` + `gh pr view --json` + targeted base-clone reads. A read-only worktree is materialized **only** when the PR modifies ``.

## Config highlights

| Key | Purpose |
|-----|---------|
| `repos[]` | Repos to scan for `review-requested:@me` PRs |
| `adjacent_reviewers` | When non-empty, a review by one at HEAD makes the loop skip (unless operator is re-requested); empty disables the gate |
| `defer_to_ci` | Wait for CI on the head commit before reviewing substance (default true) |
| `agent_backend` | `cursor` / `copilot` / `claude` (fallback chain runs cursor→copilot→claude) |
| `state_log` | JSONL idempotency log (reviewed `owner/repo#pr@sha`) |

## Where files live

| Path | Purpose |
|------|---------|
| `~/.config/ai-sdlc/pr-review-loop.yaml` | Operator overlay (machine-specific keys) |
| `~/.local/share/ai-sdlc/pr-review-loop-firings.log` | JSONL firing history |
| `~/.local/share/ai-sdlc/pr-review-loop-latest.md` | Last firing summary |

Toolkit defaults (versioned): `skills/pr-review-loop/config.example.yaml` (holds the `repos[]` list).

## Dry-run discovery (no review posted)

```bash
python3 scripts/discover_pr_review_candidates.py \
  --config ~/.config/ai-sdlc/pr-review-loop.yaml --json
```
