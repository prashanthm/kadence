---
name: product-brief-generation
description: Author a consistent product brief (product-brief.md) for an initiative, including an Epic Index that feeds epic generation. Use when defining the capability under an initiative or refreshing an existing brief.
---

# Product Brief Generation Skill

## Purpose

Define the capability an initiative delivers and register its epics at a glance, so the Epic Index can be consumed downstream by epic-generation. The Epic Index is also where release order lives (top-to-bottom = intended sequence); dates and status live in GitHub.

## When to Use

- Defining the product brief for a new initiative
- Rewriting an existing `product-brief.md` to a consistent format
- Establishing or normalizing the Epic Index before scaffolding epics

## Required Inputs

- The sibling `initiative.md` (charter) for scope and outcomes
- Organization context: `mission.md` / `platform-brief.md` when present
- Known epic-level scope (capabilities to slice into the Epic Index)
- Template: [`templates/product-brief.md`](../../templates/product-brief.md)

## Required Workflow

1. Read [`templates/product-brief.md`](../../templates/product-brief.md) and treat every `<!-- AGENT: ... -->` block as authoring rules — not as text to copy.
2. Read the sibling `initiative.md` to align the brief with the charter's What and Success Criteria.
3. Draft in fill order: Title + tagline -> Initiative pointer -> What This Capability Delivers -> Who It's For -> Components -> Epic Index.
4. Set the Initiative pointer to link `initiative.md`.
5. Build the Epic Index — one row per epic, in intended release order (release order lives here, not in a separate roadmap).
6. Strip every `<!-- AGENT: ... -->` and `<!-- REPLACE: ... -->` block; the shipped file must contain no template scaffolding.
7. Present the draft for review before writing the file.

## Epic Index Rules

- Each epic is named by a **descriptive slug** (kebab-case, e.g. `mcp-transport-core`, `agent-runtime`) — never a positional ID.
- The slug must match the intended epic doc filename stem `epics/<slug>.md` so [`epic-generation`](../epic-generation/SKILL.md) can consume it.
- Outcome is one line describing what "done" enables; Description is a scope hint only.
- Do NOT paste full acceptance criteria, full feature lists, or raw issue tables into the Epic Index — that detail belongs in `epics/<slug>.md`.
- Row order is intended release order; per-phase dates and status live in GitHub, not in this table.
- Set the Epic doc column to `epics/<slug>.md` only when that file exists, otherwise `—`.

## Document Rules

- Components table lists the moving parts and their role, not implementation detail.
- Who It's For names target users/roles.
- No placeholder template text is allowed in the shipped file.

## Verification

- [ ] File written to `initiatives/<name>/product-brief.md`
- [ ] Title, Initiative pointer, What This Capability Delivers, Who It's For, Components, Epic Index present
- [ ] Initiative pointer links the sibling `initiative.md`
- [ ] Epic Index uses descriptive slugs that map to `epics/<slug>.md`
- [ ] Epic Index rows are in intended release order
- [ ] No full acceptance criteria or feature lists in the Epic Index
- [ ] No `<!-- AGENT -->` or `<!-- REPLACE -->` text remains
