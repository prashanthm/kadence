# Board Setup Gate Checklist

> Stand up an initiative's GitHub Project board so Status is consistent and the
> **mechanical** transitions self-maintain — while the **human gates** stay manual.
> See [project-board.md](../standard/project-board.md).

## Field + items

- [ ] Project created for the initiative (org-level GitHub Project v2)
- [ ] Canonical `Status` field installed: `setup-project-board.sh --org <org> --project <N> --check` reports CONFORMANT (Backlog → Ready for Dev → In review → Done)
- [ ] Issues imported and placed in `Backlog`: `setup-project-board.sh … --repo <owner/repo> --import`

## Board entry — native Projects built-ins (Settings → Workflows; no Action)

> Entry (`Backlog`) is owned by GitHub Projects' own built-in workflows — enable them once in
> the project UI. `Backlog` is not a human gate, so a native default is safe. See
> [project-board.md → Board entry](../standard/project-board.md).

- [ ] **Auto-add to project** enabled, filter `is:issue,label:feature,epic,task` (the labels your generators apply)
- [ ] **Item added → set `Status: Backlog`** built-in enabled
- [ ] Verified: opening a new labeled issue lands it on the board in `Backlog` **without** any API `addProjectV2ItemById` call (skills must not add via API — that bypasses the trigger and leaves Status empty)

## Status transitions (shipped Action — reproducible, gate-respecting)

> The PR-driven transitions must never overwrite a human gate, which native built-ins can't
> express — so they ship as a version-controlled Action.

- [ ] Copied `templates/.github/workflows/project-status-on-pr.yml` into `<repo>/.github/workflows/`
- [ ] Set `PROJECT_ORG` + `PROJECT_NUMBER` in the workflow to this board
- [ ] **Org GitHub App** for Projects is installed on this repo, and the org secrets
      `PROJECTS_APP_ID` + `PROJECTS_APP_PRIVATE_KEY` exist (one-time org-admin setup — see
      [projects-app-auth.md](../standard/projects-app-auth.md)). No per-repo PAT needed.
- [ ] `set_project_status.py` is reachable from the workflow (toolkit checked out / vendored at `scripts/`)

## Reviewer assignment — CODEOWNERS (required for the review loop)

> The `pr-review-loop` reviews PRs where the operator is a **requested reviewer** and
> **refuses to review a PR authored by the operator** (self_pr). The build loops author PRs
> as the operator's `@me`, so GitHub must auto-request a reviewer who is **NOT** the author.
> GitHub never requests review from the PR author even if they're a code owner.

- [ ] `templates/.github/CODEOWNERS` copied to `<repo>/.github/CODEOWNERS`
- [ ] `<reviewer>` set to a handle/team that is **different from the loop's author account**
      (else no reviewer is requested and pr-review-loop finds nothing)
- [ ] `pr-review-loop` `github_user` = that reviewer, and the loop runs under that reviewer's `gh` auth
- [ ] (Optional) branch protection "Require review from Code Owners" enabled

## Verify the gate boundary

- [ ] A **draft** PR opening leaves the card at `Ready for Dev` (no premature "In review")
- [ ] Marking the draft **ready for review** moves the card `Ready for Dev` → `In review`
      (the one automated forward move off that gate — `--allow-dev-review`)
- [ ] An item in `Ready for Dev` is otherwise **never** overwritten by automation (human gates stay manual)
- [ ] A PR that `Closes #N` in its **body** moves #N even on a non-default (integration) branch —
      the workflow parses the body, not just `closingIssuesReferences` (empty off the default branch)
- [ ] Merge into a **non-default** branch (e.g. `phase2`) sets #N to `Done` but does **not** close the
      issue; merge into the **default** branch closes it (two-state train lifecycle)
- [ ] Engineering work loop (if Status-gated) only picks up `Ready for Dev` items

## Optional — markdown-driven path

