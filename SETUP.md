# Setup: Adopt the toolkit for an initiative

The lean v2 onboarding. Five steps to go from an idea to an autonomous delivery loop.

## 1. Create the initiative (product layer, in the initiatives repo)

In your initiatives repo (e.g. `product-workspace/initiatives/<slug>/`):

```
initiatives/<slug>/
  initiative.md        # why the program exists (from templates/initiative.md)
  product-brief.md     # what it delivers + Epic Index (release order by phase name)
  epics/<slug>.md      # one per capability area
  features/<slug>.md   # THE build unit: What / Why / Acceptance Criteria
```

Use the templates in `templates/`. **Slug-named, no `**Status:**`, no positional IDs, no
dates** — status/dates live in GitHub (see the glossary).

## 2. Set up the GitHub board (status automation)

The board is the source of truth for status. Create a GitHub Project (v2) with a `Status`
field: `Backlog · Ready for Dev · In review · Done` (see `standard/project-board.md`).

**Board entry** is native — enable two built-in Projects workflows once in the project UI
(**Settings → Workflows**): *Auto-add to project* (filter `is:issue,label:feature,epic,task`)
and *Item added → Status: Backlog*. New labeled issues then self-place in `Backlog`; no Action
or script on the entry path.

**Status transitions** ship as one Action — vendor it into the **code repo** and set the
org/project number:

```
cp templates/.github/workflows/project-status-on-pr.yml     <code-repo>/.github/workflows/
```

It does the mechanical PR moves (PR opened → In review; PR merged → Done via `Closes #`) and is
**gate-respecting** — it never overwrites the one human gate, **Ready for Dev**. No markdown
status, no sync job.

**INDEX.md drift check** — for repos with `initiatives/<slug>/` trees, add a thin caller
workflow that references the toolkit's published reusable workflow (vendor
`scripts/generate_initiative_index.py` and `scripts/detect_affected_initiatives.py` into your
repo's `scripts/` first):

```
# <code-repo>/.github/workflows/index-regenerate-check.yml
name: Index Regeneration Check
on:
  pull_request:
    paths:
      - "initiatives/*/epics/**"
      - "initiatives/*/features/**"
      - "initiatives/*/adrs/**"
  push:
    branches: [main]
    paths:
      - "initiatives/*/epics/**"
      - "initiatives/*/features/**"
      - "initiatives/*/adrs/**"
jobs:
  index-check:
    uses: your-org/kadence/.github/workflows/index-regenerate.yml@main
```

See the ADOPTER SETUP block in `templates/.github/workflows/index-regenerate.yml` for full
context (drift check only — never auto-commits).

## 3. Create the GitHub issues (from the docs)

One issue per epic/feature (`gh issue create` with the right label — native auto-add places it
on the board; never add via the API). The issue links out to its doc; the doc stores no issue
number — the join is **slug + branch + `Closes owner/repo#N`**. Issues start in `Backlog`.

## 4. Configure the loops

Four peer loops (`scripts/loop_registry.py`) cover the lifecycle end to end. Install the ones
you need — most adopters want all four:

**spec-loop** and **implement-loop** are engine-driven and share one setup script, selected
with `--loop`:

```
cp skills/engineering-work-loop/config.example.yaml ~/.config/kadence/spec-loop.yaml
cp skills/engineering-work-loop/config.example.yaml ~/.config/kadence/implement-loop.yaml
# set repos[].clone_path in each; spec-loop gates on "Ready for Spec", implement-loop on "Ready for Dev"
scripts/engineering-work-loop-setup.sh --loop spec-loop install
scripts/engineering-work-loop-setup.sh --loop implement-loop install
```

**pr-review-loop** and **pr-comment-fix-loop** are self-hosted (their own cron, no shared
engine):

```
cp skills/pr-review-loop/config.example.yaml ~/.config/kadence/pr-review-loop.yaml
cp skills/pr-comment-fix-loop/config.example.yaml ~/.config/kadence/pr-comment-fix-loop.yaml
# set github_user + repos[] in each
scripts/pr-review-loop-setup.sh install
scripts/pr-comment-fix-loop-setup.sh install
```

**Vendor CODEOWNERS into the code repo.** pr-review-loop only reviews PRs where its configured
`github_user` is a *requested* reviewer, and it refuses to review its own PR (self-PR guard).
Since the build loops author PRs as that same identity, GitHub must auto-request a **different**
reviewer for the review cycle to have anything to act on:

```
cp templates/.github/CODEOWNERS <code-repo>/.github/CODEOWNERS
# edit the reviewer line — must NOT be the same identity the loops author PRs as
```

Verify the toolkit itself is healthy first: `python3 scripts/doctor.py`.

## 5. Run the lifecycle

1. Move a feature's card to **Ready for Spec**. spec-loop picks it up, authors the code-repo
   `specs/<feature>/{spec,plan,tasks}.md` trio via the `spec-author` skill, and opens a
   spec-only draft PR (`Refs #N`) — no code yet.
2. Review the **plan**, not a diff. Merging that PR *is* the approval — the board automation
   promotes the card **Ready for Spec → Ready for Dev** automatically on merge.
3. implement-loop picks up the now-gated card, implements it in an isolated worktree against
   the merged spec, re-runs every Loop AC `verify:` (`--enforce`), and opens a **draft** code PR
   (`Closes #N`, gated by `report_gate.py`: real `Skill used` + diff-vs-claim).
4. Mark the draft ready — CODEOWNERS auto-requests your configured reviewer, board advances to
   **In review**. pr-review-loop reviews it; pr-comment-fix-loop addresses feedback and
   re-requests review, up to `max_rounds`.
5. Merge. The board advances to **Done** (closes the issue too, if the PR targets the repo's
   default branch — merging into a non-default integration branch instead leaves the issue open
   until it reaches the default branch; see `standard/project-board.md`).

That's it. Author intent in markdown; track state in GitHub; let the loop ship draft PRs;
merge stays human.

> Dates/progress: a GitHub Projects target-date + Roadmap view (cross-repo) or a milestone
> `due_on` (per-repo). "Launch in 30 days" = a target date held by cutting scope, not editing
> a doc. See `standard/glossary.md`.
