# Handler — dependabot

Work item type: `dependabot`

## When

Open PR author `dependabot[bot]`; semver patch/minor per config. Discovery filters these via `gh pr list --app dependabot` (the GitHub App).

## Workflow

1. Worktree item id: `dep-<pr#>`.
2. Acquire worktree on Dependabot head branch (do not create new branch).
3. Run Loop AC: CI green, semver check, optional audit.
4. Fix trivial CI failures if AC allows.
5. Push to **same branch**; comment Work Fix Report on PR.
6. Do **not** open a new PR.

## Never auto

Major semver bumps, breaking-change label, >20 files changed.
