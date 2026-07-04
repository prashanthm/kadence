# kadence (v2)

> Working name — a rename is likely. See `assessments/kadence-v2` in
> [prashanthm/product-workspace](https://github.com/prashanthm/product-workspace) for the full plan.

**A lean, autonomous, product-aware SDLC for AI-assisted teams.**

Most spec-driven tools stop at a single feature: you drive `specify → plan → tasks → implement`
by hand, one feature at a time. This toolkit does the two things they don't:

- **A product tier above the feature** — Initiative → Epic → Feature, on a GitHub board, with the
  product/engineering boundary that keeps PMs out of file paths and engineers out of business cases.
- **An autonomous, board-native delivery loop below it** — a cron picks up approved work, implements
  it in an isolated git worktree, verifies acceptance criteria, and opens a **draft** PR for review —
  unattended. Humans still decide and merge.

It is deliberately **lean**: three durable layers, one committed `specs/<feature>/` per feature in the
code repo, and status/dates/progress kept in GitHub — never re-maintained in markdown.

## The model in one breath

- **Durable (markdown, forever):** initiative · product brief (Epic Index = release order) · epics ·
  features · ADRs · `specs/<feature>/`. Slug-named. No status, dates, or positional IDs.
- **Mutable (GitHub, live):** status (issue/board) · dates & progress (Projects Roadmap + milestones) ·
  what shipped (releases/tags).
- **The join:** a slug + a branch + `Closes owner/repo#N`. The issue links out to the doc and the spec.

## Principle

**The agent proposes; the deterministic harness disposes.** Every reward — a green acceptance
criterion, "done", a board moving to Done — is backed by a command the harness re-runs and an artifact
it can see. Never by an agent's self-report.

## Status

`v2.0.0-rc1` — a release candidate. The lean core is complete: the autonomous loop engine
(ported clean, compliance stripped) as a four-loop family (spec-loop, implement-loop,
pr-review-loop, pr-comment-fix-loop), the enforcement layer (`--enforce` verify +
`report_gate`), the 3-layer authoring skills + templates, and the GitHub board automation.
`ai-sdlc doctor` gates every change (212 tests green).

```
python3 scripts/doctor.py          # tests + engine imports + skill-registry + instrumentation
python3 scripts/doctor.py --strict # also assert the v2 cuts have landed
```

**Get started:** [`SETUP.md`](SETUP.md) — five steps from an idea to a running loop.

## Layout

```
standard/     the lifecycle definition (glossary, guide, project-board, roles)
templates/    slug-named artifacts (initiative → feature, spec folder, board Actions)
skills/       the delivery engine (4-loop family) + authoring (generate/implement/decompose)
scripts/      the loop engine, doctor, event log, report gate, board mover
tests/        the suite doctor runs (212)
specs/        this repo's own specs/<feature>/ (dogfooding)
```

## What v2 removed (and why)

The markdown `**Status:**` field, the M18 status-drift metric, `issue-sync`/`sync_status.py`,
`execute_auto_compliance.py` (714 LoC), `roadmap.md`, and positional `eNN-fNN` IDs — the
bookkeeping that made v1 heavier than the Spec Kit it was built to undercut. Status, dates,
and progress now live in GitHub; markdown holds durable intent. See the initiative's
`assessments/kadence-v2` for the full rationale.
