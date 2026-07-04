# kloop (Engineering Work Loop) — Operator Guide

Automation entry: [scripts/loop-automation.md](../../scripts/loop-automation.md)

Runnable local loop: discover assignee work, implement in worktree, verify Loop AC, open draft PR.

Agent workflow: [SKILL.md](SKILL.md). Fix agent backends: [loop-agent-backends.md](../../standard/loop-agent-backends.md).

## Prerequisites

- `gh auth login`
- **Claude:** `claude auth login` (stored session) or `claude setup-token` (sets `CLAUDE_CODE_OAUTH_TOKEN` for headless) — the only backend
- A local git clone per repo (`repos[].clone_path`; falls back to `git.primary_clone`, auto-detected on install)

See [loop-agent-backends.md](../../standard/loop-agent-backends.md) for install links.

## Run every 15 minutes (macOS / Windows)

```bash
scripts/engineering-work-loop-setup.sh install
scripts/engineering-work-loop-setup.sh run
scripts/engineering-work-loop-setup.sh status
```

`install` checks CLI login, creates local dirs, writes operator config overlay (merged with toolkit defaults), installs a scheduler **every 15 min**, and runs one smoke firing. On macOS it installs launchd at `:00/:15/:30/:45`; on Windows it creates a Task Scheduler job named `kadence-engineering-work-loop` that runs every 15 minutes from install time through Git Bash (firings may not align to quarter-hour marks the way launchd does). A firing still in progress when the next tick arrives is **skipped** (single-instance lock at `~/.local/share/kadence/engineering-work-loop.lock`), so slow firings never stack. Both loops fire the same ticks; each holds its own lock, so they don't block each other.

On Windows, run the same setup entrypoint from Git Bash:

```bash
scripts/engineering-work-loop-setup.sh install
```

The setup wrapper resolves `python3`, `python`, or `py -3`, then the installer creates the scheduled task and points it at `engineering-work-loop-cron.sh` via Git Bash. If Git Bash is not on `PATH`, set `BASH_EXE` to your `bash.exe` path before running install.

## Stop the Loop

Use `uninstall` to remove the scheduler entry when you want to stop the loop:

```bash
scripts/engineering-work-loop-setup.sh uninstall
```

To pick up new defaults from the toolkit without losing your overrides:

```bash
scripts/engineering-work-loop-setup.sh install --refresh-config --skip-launchd --skip-smoke
```

Manual agent run (outside cron):

```bash
scripts/engineering-work-loop.sh
```

## Where files live

| Path | Location | In git? | Purpose |
|------|----------|---------|---------|
| `~/.config/kadence/engineering-work-loop.yaml` | Your machine | No | Operator overlay (`github_user`, `git.primary_clone`, `agent_backend`, `agent_model`) |
| `~/.local/share/kadence/` | Your machine | No | Worktrees, status logs, cron log |
| `~/.local/share/kadence/engineering-work-loop-latest.md` | Your machine | No | Last firing summary (per-item outcomes) |

Toolkit defaults (versioned, auto-merged): `skills/engineering-work-loop/config.example.yaml`. Per-repo `clone_path` and `max_items_per_repo` live here (the overlay serializer only writes the four machine-specific keys above) — edit the merged config or hand-edit the overlay to override them.

**Multi-item firings:** the loop processes up to `max_items_per_repo` items per repo per firing, sequentially (one agent process per item). A firing can therefore exceed the 30-min cadence; launchd will not double-fire the same job but may skip a tick while a long firing runs.

## Config highlights

| Key | Purpose |
|-----|---------|
| `agent_backend` | `claude` (the only backend) |
| `repos[].clone_path` | Local clone for each repo's worktrees (set in the merged config — **not** the minimal overlay; `--refresh-config` won't write it). Falls back to `git.primary_clone`. |
| `repos[].base_ref` / `git.base_ref` | Branch a new worktree forks from (`repos[].base_ref` → `git.base_ref` → `origin/main`). Discovery sets `ENGINEERING_LOOP_BASE_REF` per candidate; cron threads it into the agent env. |
| `max_items_per_repo` | Max items processed per repo per firing, sequentially (default 5) |
| `max_items_per_firing` | Legacy global ceiling — leave unset for multi-item; set to 1 to force single-item firings |
| `enabled_work_types` | chore, dependabot, feature, fix |
| `process_assist` | Pick up `assist` tier items when true (default false) |
| `pr.open_as_draft` | Loop opens draft PRs only |
| `pr.merge_policy.enabled` | Risk-based auto-land (e04-f10) — **default false** = draft-only/human-merge (unchanged) |
| `pr.merge_policy.dry_run` | Shadow mode — log the merge decision, perform no GitHub writes (default true) |

## Risk-based auto-land (e04-f10, opt-in)

When `pr.merge_policy.enabled: true`, the loop runs `assess_merge_readiness.py` **after** Loop AC and may promote+merge a PR only when **every** gate holds: tier `auto`, Loop AC passed, mergeable, CI green, **pr-review-loop APPROVED**, within task budget, base = integration branch. Any failed gate keeps the PR draft and labels it `loop-merge-blocked:<reason>`. Default OFF reproduces today's behavior exactly.

**Roll out shadow-first:**

1. `enabled: false` (default) — no change.
2. `enabled: true, dry_run: true` per repo — the loop logs `WOULD MERGE #N` / `WOULD BLOCK #N — <reason>` to the operator state log but writes nothing. Compare against your own judgement.
3. `dry_run: false` — the loop runs `gh pr ready` + `gh pr merge --<method> --delete-branch` (method from `pr.merge_policy.method`: `merge` or `squash`) on a `MERGE` verdict.

> **Gate 5 (review):** approval is verified against the **pr-review-loop operator** (config `github_user`, or `--review-operator`) at the PR's current HEAD — an unrelated team reviewer's approval, a stale approval at an older commit, or an approval whose body still lists Critical/High findings does **not** satisfy the gate.

> **Cron wiring (t03) is intentionally deferred.** The auto-land step is currently driven by the `implement-loop.prompt.md` / `SKILL.md` instructions the agent follows after Loop AC, not by a deterministic hook in `engineering_work_loop_cron.py` (unlike pr-review-loop's cron path). This is acceptable while the feature is shadow-first / default-off; a deterministic post-Loop-AC `cron` invocation is tracked as a follow-up before `dry_run: false` is recommended at scale.

## Discovery

Cron runs `discover_engineering_work_candidates.py` before the agent. It lists `@me` issues + dependabot PRs across all configured repos and **classifies** each by risk tier, applying the per-repo cap.

```bash
# Preview candidates without invoking the agent
python3 scripts/discover_engineering_work_candidates.py \
  --config ~/.config/kadence/engineering-work-loop.yaml --dry-run --json
```

## Scripts

| Script | Role |
|--------|------|
| `engineering-work-loop-setup.sh` | **Install / run / status** (start here) |
| `engineering-work-loop-cron.sh` | Scheduled entrypoint (called by launchd) |
| `engineering_work_loop_cron.py` | Sequential multi-item orchestrator (discover → per-item agent → status) |
| `discover_engineering_work_candidates.py` | Deterministic discovery + risk classification + per-repo cap |
| `loop_check.py` | Argv-only verify helpers for auto-tier Loop AC |
| `engineering-work-loop.sh` | Manual agent run |
| `invoke_loop_agent.sh` | Claude Code dispatcher |
| `worktree_acquire.sh` / `worktree_release.sh` | Isolated git work |

## Base ref override

By default the worktree forks from `origin/main`. Per-repo or global config overrides
that default (resolution: `repos[].base_ref` → `git.base_ref` → `origin/main`):

```yaml
repos:
  - owner: your-org
    repo: subsurface-agentic-ai
    clone_path: ~/projects/subsurface-agentic-ai
    base_ref: origin/phase2
git:
  base_ref: origin/main   # fallback for repos without repos[].base_ref
```

Discovery emits `base_ref` on each issue candidate; cron sets `ENGINEERING_LOOP_BASE_REF`
before invoking the agent. For a one-off manual run you can still set the env var directly:

```bash
ENGINEERING_LOOP_BASE_REF=origin/feat/my-branch \
ENGINEERING_LOOP_FORCE_ISSUE=241 \
scripts/engineering-work-loop.sh
```

**Bootstrapping note:** auto-tier Loop AC verify commands may invoke
`scripts/loop_check.py`. The worktree forks from the base ref, so
`loop_check.py` must exist on that base for `verify_loop_ac.py` to pass. Until this
feature lands on `main`, point `ENGINEERING_LOOP_BASE_REF` at the feature branch.
