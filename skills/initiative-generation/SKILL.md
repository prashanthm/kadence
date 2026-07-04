---
name: initiative-generation
description: Author a consistent initiative charter (initiative.md) for a new program of work, grounded in mission and platform context. Use when starting a new initiative or rewriting an existing charter for consistency.
---

# Initiative Generation Skill

## Purpose

Create the top-tier initiative charter that frames why a program of work exists, what it delivers, and how success is measured — the north-star document that epics, features, and ADRs trace back to.

## When to Use

- Starting a new initiative under `initiatives/<name>/`
- Rewriting an existing `initiative.md` to a consistent format
- Normalizing a charter before drafting the product brief

## Required Inputs

- The idea/why for the initiative (problem, motivation, "why now")
- Organization context: `mission.md` (goals, portfolio) and `platform-brief.md` when present
- Related initiatives this one depends on (for the Depends On table)
- Template: [`templates/initiative.md`](../../templates/initiative.md)

## Required Workflow

1. Read [`templates/initiative.md`](../../templates/initiative.md) and treat every `<!-- AGENT: ... -->` block as authoring rules — not as text to copy.
2. Read `mission.md` (and `platform-brief.md` if present) to ground the charter; identify the mission goal this initiative advances.
3. Choose the initiative slug and create `initiatives/<name>/` if it does not exist.
4. Draft the charter in fill order: Why -> What -> Success Criteria -> Depends On -> Deployment Variants -> Timeline.
5. Write Success Criteria as measurable, testable checkboxes.
6. Add a Reference table linking the sibling `product-brief.md` (may not exist yet — link it as the intended path).
7. Strip every `<!-- AGENT: ... -->` and `<!-- REPLACE: ... -->` block; the shipped file must contain no template scaffolding.
8. Present the draft for review before writing the file.
9. Write `initiatives/<name>/initiative.md` to disk after review.
10. **Required — bootstrap the initiative's `AGENTS.md` and root routing-table row.** Once `initiative.md` is
   on disk, run
   `scripts/bootstrap_initiative_agents_md.py --product-workspace-root <repo-root> --initiative-slug <slug>`
   (from the `your-org/kadence` repo). This is a required step, not optional prose: it creates
   `initiatives/<slug>/AGENTS.md` seeded from the charter's own `## Why`/`## What` (never blank
   scaffolding) and appends exactly one new row to the `product-workspace` root `AGENTS.md` routing table
   pointing at `initiatives/<slug>/INDEX.md`, without touching any other row. The script is idempotent for
   new initiatives — a re-run against an initiative that already has an `AGENTS.md` and routing-table row
   is a safe no-op for those artifacts. When rewriting an existing charter and `## Why` or `## What` changed,
   pass `--force` so `AGENTS.md` is refreshed from the updated charter (the routing row's Purpose cell is
   not updated once present — edit the root table manually if that text must change). Do not hand-write
   either file yourself; this is the lifecycle wiring that keeps the root routing table from going stale as
   initiatives are added.

## Initiative Rules

- The Why section must name which mission goal the initiative advances and why now.
- Success Criteria are measurable outcomes, not task lists.
- What describes capability and outcome — keep technical design in ADRs/architecture, not the charter.
- Timeline captures intent and phases only; execution tracking (status, dates) lives in GitHub.
- Product detail belongs in `product-brief.md` — do not duplicate it here.
- No placeholder template text is allowed in the shipped file.

## Verification

- [ ] File written to `initiatives/<name>/initiative.md`
- [ ] Why, What, Success Criteria, Depends On, Deployment Variants, Timeline present
- [ ] Why names a mission goal; Success Criteria are measurable checkboxes
- [ ] Reference/links point to sibling `product-brief.md`
- [ ] No `<!-- AGENT -->` or `<!-- REPLACE -->` text remains
- [ ] `scripts/bootstrap_initiative_agents_md.py` was run: `initiatives/<name>/AGENTS.md` exists and is
      seeded from this charter's own content, and the `product-workspace` root `AGENTS.md` routing table
      has exactly one new row for this initiative (no existing rows disturbed)
