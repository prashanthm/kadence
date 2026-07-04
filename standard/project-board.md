# Standard: Project Board (v2)

The GitHub Project board is the **single source of truth for status**. There is no
markdown `**Status:**` field and no sync — status is set by the board's own automation
(mechanical transitions) and by humans (the gates). This is what replaced v1's
markdown⇄issue status sync and the M18 drift metric.

## The canonical `Status` field

v2 collapses the old five-column flow (which had per-task `Ready for Spec` / `Approved`
gates) to four, because the task→spec layer is no longer a standard gate — a Feature is
the build unit.

| Status | Meaning | Set by |
|--------|---------|--------|
| `Backlog` | Defined, not yet approved to start | **native Projects built-ins** — Auto-add (by label) + "Item added → Backlog" |
| `Ready for Dev` | Approved to build — the loop may pick it up | **human (PO/Builder)** — the gate |
| `In review` | PR open for the linked issue | **mechanical** — `project-status-on-pr.yml` |
| `Done` | PR merged | **mechanical** — `project-status-on-pr.yml` (via `Closes #`) |

**Mechanical vs gate — the boundary the automation enforces.** `Backlog`, `In review`,
and `Done` are moved by the shipped Action. **`Ready for Dev` is the one human gate** —
nothing the loop builds advances a card *into* work without a human moving it there. The
**implement-loop** reads this Status (when `project.status_gates: ["Ready for Dev"]`) and
**only picks up issues in the allow-list** — so a feature is implemented only after a human
has cleared it.

### Optional: `Ready for Spec` — the spec-review gate (spec-loop → implement-loop)

A team that wants engineers to **review the plan before the agent writes code** can add a
`Ready for Spec` column and run the **spec-loop** (the spec-drafting member of the
kloop family). Opt-in; simple features skip it and go straight to `Ready for Dev`.

| Status | Meaning | Set by |
|--------|---------|--------|
| `Ready for Spec` | Approved to have its spec drafted (plan-review queue) | **human** — the (optional) spec gate |
| → *(spec drafted)* | **spec-loop** authors `specs/<slug>/` + opens a **spec-only** draft PR (`spec/<n>-<slug>`, `Refs #`) | spec-loop / [`spec-author`](../skills/spec-author/SKILL.md) |
| → `Ready for Dev` | engineer **merges the spec PR** → card auto-promotes; implement-loop takes over | **mechanical** — `project-status-on-pr.yml` on a merged `spec/*` PR |

Merging the spec PR **is** the human plan-approval, so that one gate-to-gate move
(`Ready for Spec → Ready for Dev`) is automated — the single exception to "automation never
sets a gate" (`set_project_status.py --spec-merge-promote`). See
[`spec-author`](../skills/spec-author/SKILL.md) and the family doc
[`engineering-work-loop`](../skills/engineering-work-loop/SKILL.md).

## Board entry — native Projects built-ins (no Action, no script)

**Entry (`Backlog`) is owned by GitHub Projects' own built-in workflows**, enabled once per
project in **Settings → Workflows**:

- **Auto-add to project** — filter `is:issue,label:feature,epic,task` (whatever labels your
  generators apply). New matching issues enter the board automatically.
- **Item added → set `Status: Backlog`** — the default-status built-in fires on entry.

`Backlog` is never a human gate, so a native built-in setting it is safe. This removes the need
for any repo Action or `set_project_status.py` on the entry path. **Skills never add an issue to
the board via the API** (`gh issue create` + the right label is enough — auto-add places it);
a raw `addProjectV2ItemById` call bypasses the "item added" trigger and lands the card with an
**empty Status**, so don't do it.

## The shipped Action (status transitions)

Ship this workflow into each initiative's code repo (`templates/.github/workflows/`):

- **`project-status-on-pr.yml`** — draft PR **marked ready** → `In review`; PR **merged** → `Done`.

The PR-transition path is a shipped Action (not a native built-in) because it must be
**gate-respecting** — it sets only the mechanical `In review`/`Done` and never overwrites a
human gate, except the narrow, human-triggered moves below. Native built-ins can't express
that guard; the entry path can use them because `Backlog` is not a gate.

**Draft vs ready.** The loop opens its code PR as a **draft** — a draft `opened` does **not**
move the card (it stays `Ready for Dev`). Marking the draft **ready for review** is the human
signal that review has started → the card advances `Ready for Dev → In review`
(`--allow-dev-review`, the one automated forward move off that gate).

**Closing links from the PR BODY, not just `closingIssuesReferences`.** GitHub only populates
`closingIssuesReferences` (and only auto-closes) for PRs targeting the **default branch**. On an
**integration branch** (`phase2`, release branches) `Closes #N` is inert. So the Action parses
`Closes #N` from the **PR body** (works on any target branch) and unions it with
`closingIssuesReferences`.

**Two-state train lifecycle (integration branches).** A merge into a **non-default** branch is
*dev-complete*, not *released*: the card goes to `Done` but the issue is **not closed**. The issue
closes only when the branch reaches the **default branch** (where native `Closes` also fires). This
avoids marking work "Done/closed" before it's actually in `main`.

**Reviewer assignment = CODEOWNERS (author ≠ reviewer).** `pr-review-loop` reviews PRs where the
operator is a requested reviewer and **refuses to review a PR it authored** (`self_pr`). The build
loops author PRs as the operator, so a **CODEOWNERS** file must auto-request a reviewer who is a
**different** identity than the loop's author (GitHub never requests the author, even as a code
owner). Ship `templates/.github/CODEOWNERS` and set the reviewer accordingly — see
[board-setup-gate.md](../checklists/board-setup-gate.md).

**Cross-repo:** these Actions and `Closes owner/repo#N` work across repositories — the
product doc's Feature issue lives in one repo, the code PR in another, and the merge still
advances the board. (Milestones are per-repo; use a Projects Roadmap for the cross-repo
view — see [glossary.md → scheduling](glossary.md).)

## Dates & release order

- **Release order** (durable) = the product brief's Epic Index, by phase name. No `roadmap.md`.
- **Dates/progress** (mutable) = a Projects target-date field + Roadmap view, and milestone
  `due_on`. Never in markdown. "Launch in 30 days" = a target-date held by cutting scope
  (drag a feature to the next iteration), not by editing a doc.

## The rule

**Author intent in markdown; track state in GitHub.** A card moves on issue/PR events and
one human gate (`Ready for Dev`). Nothing else — no markdown status, no sync job, no drift
metric, no compliance closeout.
