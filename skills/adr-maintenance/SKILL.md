---
name: adr-maintenance
description: Maintain ADR lifecycle using GitHub Issues as the source of truth. Use when creating, updating, superseding, or closing architecture decisions.
---

# ADR Maintenance Skill

## Purpose

Keep architecture decisions clear, discoverable, and collaborative by managing ADR status and discussion in GitHub Issues.

## Source of Truth Rule

- GitHub Issues are the source of truth for ADR status, rationale updates, and decision discussions.
- ADR markdown files store the durable decision record, but issue state is authoritative for workflow.

## When to Use

- Drafting a **Foundation-tier** ADR listed in an approved `initiatives/<slug>/adrs/adr-list.md` (use [`adr-list-generation`](../adr-list-generation/SKILL.md) for the catalog first).
- New architectural decision needed that is already listed in `adr-list.md`.
- Existing ADR needs clarification or scope update.
- A decision is being superseded.
- Teams disagree on architecture and need a traceable decision log.

## Prerequisites

For Foundation-tier ADRs (`foundation-adr-tier1/2/3`):

- Approved `initiatives/<slug>/adrs/adr-list.md` exists (from [`adr-list-generation`](../adr-list-generation/SKILL.md)).
- Pick one row (`ADR-NNN`) from the Proposed ADRs table before drafting.

## Scope and bypass

**Requires approved catalog** — greenfield Foundation ADRs (`foundation-adr-tier1/2/3`): approved `adr-list.md` and a Proposed row for ADR-NNN.

**Does not use this prerequisite:**

- **Brownfield** — recover the decision from existing code (`Status: Discovered` under `assessments/<system>/adrs/`) rather than requiring a catalog row.
- **Ad-hoc / urgent** — draft without a list row only when a human directs it; add the decision to `adr-list.md` on the next catalog refresh.

Do not refuse brownfield or human-directed ad-hoc drafts because the catalog is missing.

## Required Workflow

1. Confirm the target ADR-NNN exists in the approved `adr-list.md` Proposed table (or refresh the catalog first via [`adr-list-generation`](../adr-list-generation/SKILL.md)).
2. Always draft the full ADR using the template at `templates/adr.md` and present it for review before creating or modifying any files. For an **option-weighing** decision, also draft the backing research/rubric doc from `templates/adr-research.md`, save it to `initiatives/<slug>/research/adr-NNN-<short-title>.md`, and link it from the ADR's `## Research & Rubric` section. For inherited or charter decisions with no options to weigh, write "No options weighed — inherited/charter decision." in that section instead.
3. **Validate the draft** against the Quality Checklist below. Present the checklist results (pass/fail/pending per item) alongside the draft so the reviewer can see completeness at a glance. Flag any items that cannot pass until a later step (e.g. cross-links pending issue creation).
4. After approval, create the ADR markdown file using the naming convention below.
5. **Create the GitHub Issue from the ADR file.** The issue body must match the ADR content exactly —
   **except** every relative markdown link (`](adr-NNN-....md)`, `](../research/....md)`,
   `](adr-list.md)`, `](../../other-initiative/adrs/....md)`) must first be rewritten to a full
   `https://github.com/<org>/<repo>/blob/<sha>/<path>` permalink. **An issue body is not a repo
   file** — a relative link that resolves correctly when read as the ADR markdown file 404s when the
   same text is posted as an issue body (it resolves against the issue's URL, not the file's repo
   path). This applies even when the issue and the ADR live in the **same** repo, not just
   cross-repo. Pin each permalink to a SHA where the file **exists** — if the ADR/research doc is on
   an unmerged branch, resolve the SHA from that branch (`gh api repos/<org>/<repo>/branches/<branch>
   -q .commit.sha`), not `main`. Verify every permalink before posting:
   `gh api "repos/<org>/<repo>/contents/<path>?ref=<sha>"` must return a `sha`, not 404. Same-repo
   ADR cross-references without a file extension (bare `ADR-NNN` mentions in prose) do not need
   rewriting — only actual markdown link syntax `](...)` targeting a file path.

   Build the rewritten body as a **rendered copy**, not the raw file — write it to a scratch path,
   verify its links, then use that as `--body-file`:
    ```bash
    # When ADR is under initiatives/<slug>/adrs/ on product-workspace, add --label <slug>
    gh issue create --title "ADR-NNN: Decision Title" --body-file <rewritten-body>.md \
      --label adr --label <initiative-slug>
    ```
    For ADRs on a dedicated code repo (no `initiatives/<slug>/` path), use `--label adr` only.
    **Never use `--body` for issue creation** — it does not reliably handle UTF-8 characters, tables, or multi-line markdown. Always use `--body-file`.
    The **ADR markdown file itself** keeps its relative links unchanged — those resolve correctly
    *there*, as a real file in the repo tree. Only the issue-body copy is rewritten.
6. After the issue is created, put the **ADR file path in the issue body** (the issue links out to the doc). Do **not** write the issue URL back into the ADR markdown — the join is the issue→doc link + the ADR slug, so the file never needs re-touching (v2: markdown is durable, GitHub holds the mutable link/status).
7. Keep the ADR **record** status current in the ADR's own `## Status` section (`Proposed`, `Accepted`, `Superseded`, `Deprecated`) — this is the ADR decision lifecycle, not a synced workflow field. Issue/board state is separate and lives in GitHub.
7a. **When an ADR flips to `Accepted`, re-derive the features it unlocks.** Feature derivation is human-invoked, not automatic — nothing watches ADR status. So on ratification, for every epic in this ADR's **`## Applies To`** whose features were **deferred pending this decision** (the epic's Relevant-ADRs / Future-Enhancements section names it as `Proposed — features deferred`), run [`feature-generation`](../feature-generation/SKILL.md) against that epic. Pass the **existing features** as input so it derives only the **net-new** features this ADR now ratifies (it must not duplicate features already present). Then update the epic's Relevant-ADRs line for this ADR from `Proposed — features deferred` to `Accepted — features derived`.
8. When superseding, open a new ADR issue and cross-link old and new ADRs.
9. New ADRs default to `Proposed` status.
10. When updating an ADR, update the markdown file first, then rewrite links and update the issue body (same link-rewrite step as issue creation).

## GitHub Issue Content Rule

The GitHub Issue body **must be the ADR markdown file's content** — not a summary, not a reformatted
subset — **with relative links rewritten to permalinks** (see workflow step 5). It is a rendered
copy, not the raw file pasted verbatim. This ensures:

- One authoritative version of the decision text (no drift between file and issue).
- Full fidelity of tables, code blocks, and special characters.
- Reviewers see the complete decision record in the issue thread.

When updating an ADR, update the markdown file first, then update the issue body from the file.

## GitHub Issue Template (ADR)

The ADR file used as `--body-file` must contain these sections (per `templates/adr.md`):

- Decision Title (H1 heading)
- Status
- Context
- Decision Drivers
- Research & Rubric (link to `initiatives/<slug>/research/adr-NNN-*.md`, or "No options weighed — inherited/charter decision.")
- Decision
- Consequences
  - Becomes Easier
  - Becomes Harder
- Applies To
- Links
  - ADR markdown path
  - Related PRs
  - Related issues

## ADR Status Policy

- `Draft`: discussion started, no recommendation yet.
- `Proposed`: recommendation ready for review. Features that depend on it are **deferred** — the epic lists it under Relevant ADRs as `Proposed — features deferred`; no features are derived from it yet.
- `Accepted`: approved and active. On this transition, **re-derive the features it unlocks** (workflow step 7a): re-run `feature-generation` for each dependent epic, deriving only net-new features.
- `Superseded`: replaced by another ADR.
- `Deprecated`: no longer relevant.

## Cross-Link Policy

Every ADR must have bidirectional links:

- In the GitHub Issue body: `ADR File: <repo path>` (the issue links out to the doc; the doc stores no issue URL)

For superseded decisions:

- Old ADR issue: `Superseded by #<new-issue>`
- New ADR issue: `Supersedes #<old-issue>`

## Naming Convention

ADR files must be named `<adr-number>-<short-title>.md` (e.g. `005-use-event-sourcing.md`).

## Applies To Rules

The `Applies To` section lists **specs, features, systems, and related ADRs** that must conform to this decision. Do **not** reference source files or implementation paths — those belong in commits and PRs, not in the decision record.

## Quality Checklist

- [ ] Decision is in one sentence and testable.
- [ ] Decision Drivers trace the reasoning from evidence to decision.
- [ ] `Research & Rubric` links a research/rubric doc (`initiatives/<slug>/research/adr-NNN-*.md`), or states "No options weighed — inherited/charter decision."
- [ ] In the linked research doc, every rubric score traces to a cited source, measured fact, or named prior art — each source marked Strong/Moderate/Weak; no score rests on assumption.
- [ ] Thin or incomplete evidence is flagged in Open Risks rather than papered over with a verdict.
- [ ] At least two rejected alternatives with explicit rejection reasons.
- [ ] Consequences include at least one downside.
- [ ] Affected epics/features/tasks are linked.
- [ ] Issue and ADR file links are bidirectional.
- [ ] Status in issue matches status in ADR file.
- [ ] `Applies To` references only specs, systems, or related ADRs — not source files.
- [ ] Issue body contains no relative `](adr-...)` / `](../...)` / `](adr-list.md)` link (would 404 — an issue body is not a repo file); every link is a full permalink instead.
- [ ] Every issue-body permalink resolves — `gh api "repos/<org>/<repo>/contents/<path>?ref=<sha>"` returns a `sha`, not 404 (confirmed before posting, not assumed).

## Anti-Patterns

- Updating ADR markdown without updating the GitHub ADR issue.
- Marking ADR accepted without recording rejected alternatives.
- Recording an option-weighing decision without a linked research/rubric doc, or putting the option-scoring matrix in the ADR body instead of the research doc.
- Recording a decision without documenting the drivers that led to it.
- Superseding an ADR without linking both records.
- Duplicating discussion in multiple places instead of centralizing in one issue thread.
- Listing source file paths in `Applies To` instead of specs, systems, or related ADRs.
- Using `gh issue create --body "..."` instead of `--body-file` — causes encoding issues with UTF-8 characters, tables, and multi-line content.
- Writing a different or abbreviated version of the ADR in the issue body instead of using the file's content.
- Posting the raw ADR markdown file verbatim as the issue body — its relative links (`](adr-033-....md)`, `](../research/....md)`) 404 once posted, since the issue body resolves links against the issue's URL, not the ADR file's repo path. Rewrite to permalinks first, even for same-repo ADRs.
