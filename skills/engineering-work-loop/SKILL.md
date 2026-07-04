---
name: engineering-work-loop
description: The kloop FAMILY (a.k.a. engineering-work-loop) — four peer loops over one shared engine (spec-loop, implement-loop, pr-review-loop, pr-comment-fix-loop). Each is a git-worktree polling loop that verifies Loop AC and opens a draft PR; operator marks ready, human merges. implement-loop is the default (build) member.
---

# kloop — the engineering work loop family

**kloop** (legacy name: `engineering-work-loop`) is the **family** of four peer loops
that share one engine (discovery, worktree, verify, report gate, config, cron/launchd/
Task-Scheduler install). Each loop is a thin descriptor over that engine — see
[`scripts/loop_registry.py`](../../scripts/loop_registry.py). The skill, the setup
scripts, and the `ENGINEERING_LOOP_*` env vars keep the `engineering-work-loop` stem;
`kloop` is the brand for the family and an accepted family selector.

| Loop | Gate | Skill | Prompt | Opens |
|------|------|-------|--------|-------|
| **spec-loop** | `Ready for Spec` | [`spec-author`](../spec-author/SKILL.md) | `spec-loop.prompt.md` | spec-only PR (`Refs #`) |
| **implement-loop** (default) | `Ready for Dev` | [`implement`](../implement/SKILL.md) | `implement-loop.prompt.md` | code PR (`Closes #`) |
| **pr-review-loop** | — | [`pr-review`](../pr-review/SKILL.md) | (self-hosted runner) | PR review |
| **pr-comment-fix-loop** | — | [`pr-comment-fix-loop`](../pr-comment-fix-loop/SKILL.md) | (self-hosted runner) | comment fixes |

Install a family loop with `engineering-work-loop-setup.sh --loop <name> install` (spec-loop /
implement-loop run over the shared engine; pr-review-loop / pr-comment-fix-loop have their own setup
scripts). `kloop` (or the legacy `engineering-work-loop`) names the family, not a concrete loop — a bare install is `implement-loop`.

## Purpose (the default member: implement-loop)

The **implement-loop** polls GitHub for assignee-owned work across one or more repos, classifies risk,
implements each item in an **isolated worktree** (the repo's clone untouched) via [`implement`](../implement/SKILL.md),
verifies **Loop AC**, and opens a **draft** code PR (`Closes #<feature-issue>`) with a **Work Fix Report**.
Operator marks ready for review; human merges. Symmetric to [pr-review](../pr-review/SKILL.md).

## When to Use

- Local scheduler during work hours (:00/:15/:30/:45 on macOS launchd; every 15 min via Windows Task Scheduler)
- Operator runs multiple manual feature branches — loop must not checkout primary clone

## Required Inputs

- Config: `config.example.yaml` (operator overlay via `engineering-work-loop-setup.sh install`)
- `gh` authenticated as operator
- A local clone per repo (`repos[].clone_path`, else `git.primary_clone` fallback)
- Prompt: `.github/prompts/implement-loop.prompt.md` (spec-loop uses `spec-loop.prompt.md`)
- **`scripts/loop_check.py` must exist on the worktree base ref** (`origin/main`, or `ENGINEERING_LOOP_BASE_REF`). Auto-tier Loop AC verify commands may invoke it; if it's absent on the base ref, those verify commands fail and the items are skipped. The cron logs a `::warning::` at startup when it's missing. Once this toolkit is merged to `main` the default base ref satisfies this automatically.

## Required Workflow

The cron does discovery and orchestration; the agent (this skill) handles one pinned item per invocation.

1. **Cron pre-flight:** `gh auth status`.
2. **Cron discovery:** `discover_engineering_work_candidates.py` lists `@me` issues + dependabot PRs across all configured repos and **classifies** each (internally via `classify_work_item.py`). It applies the per-repo cap (`max_items_per_repo`, default 5) and attaches each candidate's `clone_path`. **Optional Project-Status gate:** when `project.status_gates` is set in config, discovery also reads each issue's `Status` on the named org GitHub Project and **skips** any issue not in the allow-list (e.g. only `Ready for Dev`) — so a task is implemented only after a human clears it (its spec/feature/task doc reviewed + merged). Gating is **off by default** (empty `status_gates`); it fails closed (an issue absent from the board is skipped). See [project-board.md → Loop integration](../../standard/project-board.md#loop-integration-engineering-work-loop).
3. **Cron loop:** for each selected candidate (sequentially, error-isolated), invoke the agent once, pinned to that issue and its `clone_path`.
4. **Agent — acquire worktree:** `worktree_acquire.sh "$CLONE_PATH" "$ITEM_ID" "$BRANCH"` (only `git fetch` in the clone; all edits in the worktree).
5. **Agent — implement:** run the handler from `handlers/` for the work type.
6. **Agent — verify:** `verify_loop_ac.py --body-file issue.md --cwd "$LOOP_CWD" --require-all --enforce --risk-tier <tier> --config <loop-config>`. **`--enforce` (v2 anti-reward-hack):** every AC must carry a `verify:` command the harness re-runs — a missing command FAILs (never skips), a `human-only` item FAILs (needs human sign-off), and the agent's `[x]` is advisory: only the harness exit code counts. (`auto` uses `verify.auto_allowed_prefixes`; auto-tier verify commands are single argv-style — use `loop_check.py` for compound checks.)
7. **Agent — publish gate + draft PR:** first run `report_gate.py --report-file report.md --skills-dir skills/ --cwd "$LOOP_CWD"` — it **rejects** a Work Fix Report that omits the required **Skill used** field, names a non-existent skill, or claims files absent from `git diff` (diff-vs-claim). Only on OK, `gh pr create --draft` with the [Work Fix Report](../../templates/work-fix-report.md). Do not request reviewers.
7b. **Agent — risk-based auto-land (opt-in, default OFF):** when `pr.merge_policy.enabled: true`, run `assess_merge_readiness.py` (e04-f10). It returns `MERGE` only when every gate holds (tier `auto`, Loop AC passed, mergeable, CI green, pr-review-loop APPROVED, within budget, base = integration branch). In `dry_run` (shadow) mode it only logs the verdict; otherwise on `MERGE` the loop runs `gh pr ready` + `gh pr merge --merge --delete-branch`, and on `BLOCK` it leaves the PR draft + labels it `loop-merge-blocked:<reason>`. Default (`enabled: false`) skips this step entirely. See [implement-loop.prompt.md → Risk-based auto-land].
8. **Agent — release worktree:** `worktree_release.sh "$CLONE_PATH" "$ITEM_ID"`.
9. **Cron status:** per-item outcomes recorded in the firing report + `firing_log`.

## Handlers

| Work type | Handler |
|-----------|---------|
| chore | [handlers/chore.md](handlers/chore.md) |
| dependabot | [handlers/dependabot.md](handlers/dependabot.md) |
| feature | [handlers/feature.md](handlers/feature.md) |
| fix | [handlers/fix.md](handlers/fix.md) |

## Scripts

| Script | Role |
|--------|------|
| `discover_engineering_work_candidates.py` | Discovery: classify + per-repo cap + Project-Status gate |
| `engineering_work_loop_cron.py` | Sequential multi-item orchestrator (called by cron) |
| `worktree_acquire.sh` / `worktree_release.sh` | Isolated checkout / cleanup |
| `verify_loop_ac.py` | Auto-tier AC gate (re-runs every `verify:` independently) |
| `loop_check.py` | Argv-only verify helpers for auto-tier Loop AC |
| `loop_events.py` | Append-only JSONL event log (instrumentation) |
| `report_gate.py` | Publish gate: require Skill-used + diff-vs-claim (force-skill-use) |
| `invoke_loop_agent.sh` | Agent run wrapper / backend dispatcher |
| `classify_work_item.py` | Risk tier (internal to discovery) |

## Never

- Merge PRs — **except** risk-based auto-land when `pr.merge_policy.enabled: true` and `assess_merge_readiness.py` returns `MERGE` (auto tier + Loop AC + mergeable + CI green + pr-review APPROVED + within budget). Default OFF.
- Mark PR ready for review (`gh pr ready`) or request reviewers — operator promotes draft when satisfied (except the auto-land gate above)
- Checkout/switch the candidate's clone (except fetch) — all edits in the worktree
- Check AC without running verify commands
- Enable the loop on repos where issues assigned to `@me` can be edited by untrusted outsiders (verify commands run locally)
- Run `assist`-tier author-provided verify commands without `--allow-assist-shell`

## Related

- Feature: [e04-f08](../../../initiatives/ai-native-development/features/e04-f08-engineering-work-loop.md)
- Loop AC template: [templates/github-issue-loop-ac.md](../../templates/github-issue-loop-ac.md)
- Work Fix Report template: [templates/work-fix-report.md](../../templates/work-fix-report.md)
- Agent backends: [standard/loop-agent-backends.md](../../standard/loop-agent-backends.md)
