# Glossary (v2)

The locked vocabulary. v2 is deliberately lean: **three product layers**, engineering
detail in a committed code-repo spec folder, and status/dates/progress in GitHub — never
re-maintained in markdown.

## Product layer — lives in `initiatives/<slug>/` (PM-owned, durable intent)

| Term | Definition | Template |
|------|------------|----------|
| **Initiative** | Time-bounded program that adds a capability. Has a product brief and epics. | [initiative.md](../templates/initiative.md) |
| **Product Brief** | What a capability delivers, who it's for, and its **Epic Index — the durable release order, by phase name (no dates)**. | [product-brief.md](../templates/product-brief.md) |
| **Epic** | A capability area within an initiative — contains features, never closes. Its **GitHub issue lives in product-workspace** (governance tier) + a milestone/phase. | [epic.md](../templates/epic.md) |
| **Feature** | **The build unit.** A deliverable with acceptance criteria. One feature → one PR → `Closes #`. Its **GitHub issue lives in the code repo** (the agent's build context; same-repo `Closes`). | [feature.md](../templates/feature.md) |

## Engineering layer — lives in the **code repo** (agent-authored, committed)

| Term | Definition | Template |
|------|------------|----------|
| **Spec folder** | `<code-repo>/specs/<feature-slug>/` — `spec.md` (what/AC for engineers), `plan.md` (files·steps·ADRs·edge-cases), `tasks.md` (granular `[P]`-parallel units). | [spec.md](../templates/spec.md) |
| **Task** | A granular implementation **step inside `tasks.md`** — NOT a standard layer. It is the ordered/`[P]` step breakdown *within* one already-right-sized feature (sizing happens at generation, not here). Each carries a `## Loop AC`. | — |
| **Loop AC** | The machine-verifiable contract: **behavioral** `verify:` commands the loop re-runs (tests pass / file exists / lint clean). The agent's `[x]` is advisory. There is **no** diff-size tripwire — size is never a gate. | [github-issue-loop-ac.md](../templates/github-issue-loop-ac.md) |
| **ADR** | Architecture Decision Record — a decision, its context, consequences. A guardrail that constrains specs; not a pipeline stage. | [adr.md](../templates/adr.md) |

## Identity, ordering, scheduling (no positional IDs, no dates in markdown)

| Concern | Home | Form |
|---------|------|------|
| **Identity** | markdown | a descriptive **slug** (`langgraph-runtime`) — never `eNN-fNN` |
| **Order** | GitHub + markdown | issue **dependencies** (`blocked by`) + `Depends On`; the `Ready for Dev` gate enforces it |
| **Date** ("ship by when") | **GitHub only** | a Projects target-date + Roadmap view; milestone `due_on` |
| **Proof** ("what shipped") | GitHub | a Release + tag |
| **Status** | **GitHub only** | the issue/board — never a markdown `**Status:**` field |

## The join

A feature's product half (What/Why/AC) is in `initiatives/`; its engineering half (the
spec folder) is in the code repo. The **single join** is the GitHub issue: slug + branch
+ `Closes owner/repo#N`. The issue links out to the doc and the spec; neither markdown
file hardcodes an issue number. Because status is not in markdown, nothing re-touches
these files — so nothing drifts.

## Where issues live + cross-repo references

For a **dedicated-code-repo** initiative, issues split by tier:

| Issue | Repo | Rationale |
|-------|------|-----------|
| **Epic** (+ ADRs, docs) | product-workspace | the durable governance graph |
| **Feature** | the **code repo** | the agent's build context; the loop `Closes <code-repo>#<feature>` **same-repo** so the board self-heals |

**All GitHub cross-repo references are ABSOLUTE — never relative markdown links.** A feature
issue in the code repo references its epic as `owner/product-workspace#<epic-issue>` (and a
cross-repo **sub-issue** relation), and any doc/ADR as a full `https://…/blob/<sha>/…`
permalink. A relative link (`](../epics/x.md)`) is a *repo-file* path — it **404s** in an
issue/PR body (a body is not a file) and rots when doc text is reused across repos. The
durable markdown docs keep their relative links (they resolve *there*); only the cross-repo
**issue/PR body** uses absolute refs. `report_gate.py` rejects a body with a relative
`](../…)` link. (Ratified in ADR-001 §Consequences: code-repo issues/PRs reference
product-workspace by absolute ref.)

## What v2 removed (and why)

- **`**Status:**` in markdown** and the M18 status-drift metric — status is the issue's job.
- **`roadmap.md`** — a schedule changes, so it lives in GitHub (release *order* is the Epic Index).
- **Positional `eNN-fNN` IDs** — a redundant identity that breaks on reordering; slugs replace them.
- **The compliance loop** (`issue-sync`, `sync_status.py`, `execute_auto_compliance.py`, synthesize) — it manufactured its own work and shipped no product.
