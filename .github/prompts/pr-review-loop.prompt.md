You are running a **periodic PR review readiness scan** across one or more repositories. Your job is *not* to review every open PR every time — it is to decide which PRs need a review action right now, and to skip the rest cleanly.

**Automated cron firing:** when the prompt ends with **Pinned candidate (automated cron firing — NON-INTERACTIVE)**, that section overrides this scan. Post exactly one `gh pr review` for the pinned PR and exit — do not scan other repos or ask the operator for confirmation.

This prompt is a wrapper around `pr-review.prompt.md`. Use that prompt's findings-first format whenever you do post a review.

## Inputs

- A list of repositories to scan, the acting reviewer's GitHub login, and related settings
  (`defer_to_ci`, `adjacent_reviewers`, `state_log`) — **all read from the config file at
  `$PR_REVIEW_LOOP_CONFIG`** (the wrapper script sets this env var; if unset, default to
  `~/.config/kadence/pr-review-loop.yaml`). **Never infer the repo list or acting login any
  other way** — do not run an account-wide `gh search prs --review-requested=<you>` across every
  repo you can see; that scans repos the operator never configured this loop for. Scope strictly
  to `repos:` in the config, one `gh pr list --repo <owner>/<repo> --search
  "review-requested:<github_user>"` per configured repo (this is exactly what
  `scripts/discover_pr_review_candidates.py --config "$PR_REVIEW_LOOP_CONFIG"` does — prefer
  running that script over hand-rolled `gh` calls, since it also applies the decision matrix
  below deterministically).
- A standing rule set (provided per-session) covering anything outside the defaults below — for example, "the merge action is the author's, never the reviewer's."

## Pre-flight on every firing

Before scanning open PRs, ensure the toolkit conventions you'll apply are current:

- The `kadence` checkout at `$TOOLKIT_ROOT` (this repo — the source of these prompts,
  the canonical templates, and the convention docs) is on its default branch and freshly pulled
  (`git fetch origin && git checkout main && git pull`). A loop running against a stale toolkit
  produces feedback against last week's conventions, which is worse than no feedback. Refresh
  first, scan second.
- If a PR being scanned itself modifies the toolkit (`is_toolkit_pr`), refresh again after that
  PR's branch is checked out (in a read-only worktree, per the toolkit-PR exception below) for
  the review pass, so the review reads the version under review rather than the prior default
  branch.

## What the loop does on each firing

For each repo, list open PRs with their HEAD commit SHA, `reviewRequests`, draft state, and recent reviews. Apply the decision matrix below per PR. The firing reviews **every eligible PR** across all configured repos (one focused review each), posting **at most one review per PR per HEAD**; default to "no action" when in doubt.

## Decision matrix

Skip the PR if **any** of:

- **Draft** (`isDraft: true`).
- **Self-PR** — the PR's author equals the acting reviewer.
- **Acting reviewer already approved at HEAD** — the most recent review by the acting reviewer is APPROVED and its `commit.oid` matches the current `headRefOid`.
- **Acting reviewer already requested changes at HEAD, and was not re-requested** — most recent review is CHANGES_REQUESTED, *and* the acting reviewer is not in the current `reviewRequests` array. Wait for the author to click "Re-request review."
- **CHANGES_REQUESTED at an older HEAD, no re-request** — same as above; new commits without an explicit re-request are not a review trigger.
- **Stale review at an older HEAD, no re-request** — any prior review (including APPROVED) at an older commit without a current `reviewRequests` entry is not a trigger; the author must re-request.
- **CI pending** (when `defer_to_ci: true`) — deterministic discovery skips while any status check is `IN_PROGRESS` / `QUEUED`; wait for CI to settle before reviewing substance.
- **Adjacent reviewer reviewed at HEAD** (when `adjacent_reviewers` is configured) — a configured adjacent reviewer already reviewed the current head commit. Skip applies only when the acting reviewer is **not** currently in `reviewRequests`; an explicit re-request overrides this gate.
- **Out of scope** — enforced by the search filter (`review-requested:<operator>`); PRs not requesting the acting reviewer are not discovered.

Otherwise, review at HEAD per `pr-review.prompt.md`, with the additional Loop Discipline section therein (findings continuity, head-SHA citation, CI deference, etc.).

## Gathering context (no worktree by default)

A reviewer posts a review; it does **not** edit, commit, or push. So do not acquire a worktree for the common case. Read the PR via `gh`:

```bash
gh pr diff <N> --repo <owner>/<repo>                     # the changeset under review
gh pr view <N> --repo <owner>/<repo> --json \
  title,body,files,commits,reviews,statusCheckRollup,headRefOid   # intent, prior rounds, CI
```

- Use the diff as the primary subject of the review. For cross-file context the diff lacks (is this symbol used elsewhere? does this break a caller?), read the **surrounding files from the operator's base clone** (the workspace passed to you) — do not check out the PR branch.
- Honor the CI-deference rule using `statusCheckRollup`; honor findings continuity using prior `reviews`.
- **Exception — toolkit PRs:** a PR in the `kadence` repo itself, or (legacy) one that
  modifies a vendored `kadence/` subdirectory in another repo (`is_toolkit_pr`),
  materialize a **read-only** worktree at the PR HEAD so you review the conventions/prompts as
  they would land, then release it:
  ```bash
  WT=$(scripts/worktree_acquire.sh "$PRIMARY_CLONE" "review-<N>" "$HEAD_BRANCH")
  # read only — never edit/commit/push
  scripts/worktree_release.sh "$PRIMARY_CLONE" "review-<N>" --force
  ```

Post the review with `gh pr review <N> --repo <owner>/<repo> {--approve|--request-changes|--comment} --body-file <review.md>`.

## State to track between firings

A small per-PR memo is enough:

| Field | Example |
|---|---|
| Last action | `Round-2 Request Changes posted` |
| At commit | `28cb004` |
| Open findings | `M1 (duplicate test file)`, `M3 (committed test-results.xml)` |
| Next trigger | `divbell re-added to reviewRequests OR HEAD advances past 28cb004 AND re-request received` |

This is the contract the next firing relies on. If the next firing sees the same HEAD with no re-request, it skips. If the HEAD advanced but no re-request, it still skips (the author may be mid-fix). If the HEAD advanced *and* the acting reviewer is back in `reviewRequests`, it re-reviews.

## Cadence

- Default: every 10 minutes during active work hours; back off to 30+ minutes if the open set is quiet for a sustained period.
- Don't fire on push notifications. Push notifications fire on intermediate commits; the polling pattern's whole point is to wait for the author's "done" signal.

## What the loop does NOT do

- It does not merge. The merge decision rests with the team that owns the consequence — typically the PR author, possibly with explicit sign-off from a senior or boss. The loop's review is informative.
- It does not run CI, re-run failed checks, or comment on CI status unless a CI-status finding is being raised explicitly.
- It does not subscribe to or react to push events. Polling is the discipline.
- It does not message the author outside the PR (no DMs, no Slack pings). All loop output is in the PR.
- It **never puts a local filesystem path (PII)** in a review comment — no operator clone/worktree path, home dir, username, or absolute `/Users/…` / `/home/…`. Reference paths repo-relative.
- It **never uses a relative markdown link** to another repo's doc/issue in a comment — cross-repo references are absolute (`owner/repo#N` or a resolving `https://…/blob/<sha>/…` permalink), because a comment is not a repo file (a relative `](../…)` link 404s).

## When the loop should explicitly do nothing

After scanning both repos, if no PR meets the review criteria, report `no actionable work` in one line and end the firing. Silence in this loop is a healthy signal, not a bug.

## Logging the loop's own state

It is useful — but not required — for the loop to maintain a one-line-per-PR state log between firings:

```
edi-mcp-server#164  R3-CHANGES_REQUESTED  @28cb004  open: M1, M3  next: re-request OR new-HEAD+re-request
product-workspace#52  awaiting-team-acks  @e96c026  no findings  next: re-request OR thread-discussion-resumes
```

This is for the operator's benefit, not the team's. Keep it terse and out of the PRs themselves.

## Operator overrides

The operator running the loop may set per-firing constraints — for example, a one-time directive to skip a specific PR, focus only on a specific repo, or pause the loop entirely. Treat operator directives as authoritative; they override the decision matrix above.

## Composition with the base review prompt

When the decision matrix says "review," follow `pr-review.prompt.md` for review *content*. The loop prompt governs *when* to review; the base prompt governs *what* a review looks like.
