You are running a **periodic PR comment fix scan** on the operator's machine. Your job is to pick up **one** operator-authored open PR with ≥2 non-operator review submissions, fix the feedback in an **isolated git worktree**, prepare a **PR Comment Fix Report**, re-request the original reviewer(s) when configured, and **never merge**. This cycle **re-engages on each genuinely-new review round** (the PR head advanced past the last completed fix **and** there is fresh non-operator `CHANGES_REQUESTED`/feedback), up to `max_rounds` (default 3). Past the cap the cron applies the `needs_human` label and the loop stops. It does **not** re-run for the same round (same head, no new feedback).

This prompt is the author-side complement to `pr-review-loop.prompt.md` (reviewer-side). The review loop waits for re-request; this loop performs the re-request after fixes.

## Inputs

- Config path (`PR_FIX_CONFIG` or `~/.config/kadence/pr-comment-fix-loop.yaml`): `github_user`, `repos[]`, `min_reviewer_feedback`, `exclude_reviewers`, `max_files_changed`, `max_rounds`, `labels` (incl. `needs_human`), `state_log`, `git.primary_clone`, `git.worktree_root`, `report.submit`, `report.draft_path`, `report.branch_draft_dir`, `max_items_per_firing`.
- Env: `PR_FIX_REPORT_DRAFT=1` forces draft report mode (same as `report.submit: false`).
- Scripts (repo-relative to `$TOOLKIT_ROOT`, the toolkit's own root — this is a standalone
  repo, not a product-workspace subdirectory): `discover_pr_fix_candidates.py`,
  `worktree_acquire.sh`, `worktree_release.sh`, `pr-comment-fix-loop-cron.sh`,
  `pr-comment-fix-loop-submit.sh`, `pr-comment-fix-loop-publish.sh`.
- Report template: `templates/pr-comment-fix-report.md`.

## Hard rules

1. **Never** run `git checkout`, `git pull`, or `git merge` in the **primary clone** — only `git fetch` there.
2. All branch/commit/push work happens in a **worktree** via `worktree_acquire.sh`.
3. Push to the **existing PR head branch** — do not open a new PR.
4. **Never merge**, approve, or run `gh pr ready`.
5. At most **one** PR per firing (`max_items_per_firing: 1`).
6. Operator login is **never** counted toward the ≥2 reviewer feedback threshold.
7. Review state (`APPROVED`, `CHANGES_REQUESTED`, `COMMENTED`) does **not** skip discovery — evaluate findings in the fix phase.
8. **Never put local filesystem paths in a PR comment/body (PII).** Do **not** include the operator's clone/worktree path (`$WT`, `$CLONE_PATH`), home dir, username, or any absolute `/Users/…` / `/home/…` path in a commit message, PR comment, or the ready comment. Paths are repo-relative.
9. **Cross-repo references must be ABSOLUTE, never relative links.** Any epic/feature/ADR/doc in another repo (e.g. product-workspace) is `owner/repo#N` or a full `https://github.com/…/blob/<sha>/…` permalink that **resolves** — never a relative `](../…)` link (a comment/body is not a repo file → 404).

## Pre-flight

1. `gh auth status`
2. Load config from `PR_FIX_CONFIG` or default path.
3. `git fetch origin` in the candidate repo's clone only (`PR_FIX_CLONE_PATH`, set by the cron from the repo's `clone_path`; falls back to `git.primary_clone`).

## Discovery

```bash
python3 scripts/discover_pr_fix_candidates.py \
  --config "$PR_FIX_CONFIG" ${PR_FIX_FORCE_PR:+--force-pr "$PR_FIX_FORCE_PR"} --json
```

Counts all non-operator review submissions + issue/inline comments (`user.login != github_user`). Trust skip gates. If `candidate` is null, report `no actionable work` and exit.

The returned candidate already carries `comment_inventory` (every non-operator review/comment)
— there is no separate context-assembly step. Read the PR's linked spec/feature issue directly
(`gh issue view`, `gh pr view --json body,files`) for traceability/requirements context as needed.

## Decision matrix

Skip if: draft, not operator-authored, completed **for the same round** (complete label/state log with head unchanged & no fresh feedback), `needs_human` label (max rounds reached), in-progress lock (&lt; stale hours), `reviewer_feedback_count < min_reviewer_feedback`, too many files, deferred/blocked. **Re-engage** when a new round is detected under `max_rounds` (discovery sets the candidate's `round`).

Otherwise: worktree → fix → verify → push → report → (submit or draft per config).

## Evaluate findings

For each `comment_inventory` / `review_findings` item:

1. Classify severity and type.
2. Disposition: **Fix**, **Defer**, or **No-change**.
3. Build **Fix Cross-check Matrix** before implementing.
4. Record severity on every finding (Critical / High / Medium / Low / Info).

### Optional / non-blocking follow-ups

Reviewers often add sections titled **Optional follow-ups**, **Optional**, **Nice to have**, or **non-blocking**.

| Situation | Disposition |
|-----------|-------------|
| Same PR scope, docs-only or within `max_files_changed`, no new CI/tooling | **Fix** — include in diff and disposition table |
| Cross-repo sweep, new lint/check infrastructure, or blocked on unmerged work | **Defer** — document rationale and follow-up |
| Pure praise or already satisfied by another fix | **No-change** |

Do not silently skip optional items; every item gets an explicit row in the disposition table.

## Re-review policy

Re-request reviewers **only** when re-review is warranted:

| Condition | Re-request? |
|-----------|-------------|
| Latest review from any non-operator reviewer is not `APPROVED` | **Yes** |
| Any **Critical** or **High** finding disposition is **Fixed** | **Yes** |
| All latest reviews are `APPROVED` and only Low/Medium/Info/unknown fixes (or none) | **No** |

In the report, include a machine-readable block (required):

```json pr-fix-rereview
{
  "required": false,
  "reason": "approved_no_critical_high_fixes",
  "all_reviews_approved": true,
  "fixed_severities": ["low", "low"],
  "reviewers": []
}
```

Set `"required": true` and list `reviewers` only when the table above says re-request. In draft mode, use **Re-request** (not "Would re-request") with either reviewer logins or `skipped — <reason>`.

## Worktree workflow

Default config has `report.submit`, `report.push`, and `report.apply_labels` set to **true** — push, post comment, apply labels, and re-request per policy when the run completes.

When all three are **false** (`PR_FIX_REPORT_DRAFT=1` or draft overlay), **do not push or call `gh`** — commit locally only.

Otherwise apply `pr-fix-cycle-in-progress` label **before** worktree:

```bash
# On a new round (round 2+) also clear the stale complete label (safe on round 1 — gh tolerates removing an absent label):
gh pr edit <N> --repo <owner>/<repo> --add-label pr-fix-cycle-in-progress --remove-label pr-fix-cycle-complete

CLONE_PATH="${PR_FIX_CLONE_PATH:-$PRIMARY_CLONE}"   # candidate repo's clone (multi-repo); else git.primary_clone
WT=$(scripts/worktree_acquire.sh \
  "$CLONE_PATH" "prfix-<N>" "$HEAD_BRANCH")
cd "$WT"
# implement Fix items; verify
git add -A && git commit -m "fix(pr-<N>): address review feedback"
# push only when report.push is true:
git push origin HEAD
```

Write `~/.local/share/kadence/pr-fix-reports/<repo>-<pr>-meta.json` with `worktree` path when staying local-only.

## Draft report mode (`report.submit: false` or `PR_FIX_REPORT_DRAFT=1`)

Worktree + local commits run; **nothing hits GitHub** until the operator publishes.

1. Write report using `templates/pr-comment-fix-report.md` with header: `> **DRAFT** — not yet posted to PR conversation`
2. Include **AI Attribution** (Author row: configured `agent_backend` / `agent_model` — Tool is `Claude Code`)
3. Commit to `<branch_draft_dir>/<pr>-draft.md` in the worktree (included in human push)
4. Write firing evidence: `<branch_draft_dir>/<pr>-firing-latest.md` and `<pr>-firing-<ISO8601>.json` (cron backfills if omitted)
5. Copy draft to `~/.local/share/kadence/pr-fix-reports/<repo>-<pr>-draft.md`
6. **Do not** `git push`, **do not** `gh pr comment`, **do not** apply labels, **do not** re-request reviewers
7. End with operator steps:

```bash
# prepare publish script + ready comment (no GitHub writes)
scripts/pr-comment-fix-loop-submit.sh <N>
# after reviewing diff + publish.sh:
PR_FIX_PUBLISH=1 scripts/pr-comment-fix-loop-publish.sh <N>
```

## Submit mode (`report.submit: true`)

Requires `report.push: true` and `report.apply_labels: true`. After push + verify:

```bash
gh pr comment <N> --repo <owner>/<repo> --body-file <report>
# Re-request only when pr-fix-rereview.required is true (see Re-review policy)
gh pr edit <N> --add-reviewer <from pr-fix-rereview.reviewers>
gh pr edit <N> --add-label pr-fix-cycle-complete --remove-label pr-fix-cycle-in-progress
```

Log `status: complete` to `state_log`. Set `rounds` to the candidate's `round` value from discovery (prior rounds + 1; `1` on the first cycle). Record `head_after_fix` as the pushed head SHA (full SHA preferred). Include `rereview_required` and `reviewers_rerequested` (may be empty when skipped).

## State log

```json
{"owner":"your-org","repo":"product-workspace","pr":129,"head_at_fix":"abc1234","head_after_fix":"def5678","reviewer_feedback_count":2,"rounds":1,"status":"complete","rereview_required":true,"reviewers_rerequested":["nidhikaul","divbell"],"completed_at":"..."}
```

## What NOT to do

- Do not merge PRs.
- Do not run a second cycle for the **same round** (same head, no fresh feedback). **Do** re-engage on a genuinely-new round under `max_rounds`; past the cap the PR carries `needs_human` and is left for a person.
- Do not react to webhooks.
- Do not checkout primary clone for edits.

## Composition

| Concern | Source |
|---------|--------|
| **When** to act | this prompt + `discover_pr_fix_candidates.py` |
| **What** to fix | disposition from discovery + context pack |
| **Where** to git | worktree scripts only |
| **When** re-review | `pr-review-loop.prompt.md` (after re-request) |
