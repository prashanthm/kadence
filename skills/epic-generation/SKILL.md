---
name: epic-generation
description: Generate consistent epic artifacts from initiative context with GitHub Issues as source of truth. Use when drafting a new epic or refreshing an existing epic from prior decisions.
---

# Epic Generation Skill

## Purpose

Create epics that are structurally consistent, historically grounded, and traceable to ADRs and GitHub issues. Each epic is named by a descriptive slug and links back to its parent product brief.

## When to Use

- Creating a new epic under an initiative
- Rewriting an epic from issue history after drift
- Normalizing epic format before issue creation/update

## Required Inputs

- Initiative context: `initiative.md` and `product-brief.md` (Epic Index row for this epic)
- Related prior epics/features in the same initiative — the fast path for this is the initiative's
  `INDEX.md` (`initiatives/<slug>/INDEX.md`); see workflow step 1a below.
- ADR source: `adrs/adr-list.md` and specific ADR files when present
- Related GitHub issues (if available)

## Required Workflow

1. Collect context from initiative docs, ADRs, and related issues. Identify the Epic Index row (descriptive slug) this epic corresponds to.
1a. **Required — read `INDEX.md` before drafting.** Read the initiative's `INDEX.md`
    (`initiatives/<slug>/INDEX.md`) and scan its Epics and Features tables for a row whose scope appears to
    already cover what this epic is about to define. If `INDEX.md` does not exist yet for this initiative
    (bootstrap case), **proceed with a noted caveat** ("`INDEX.md` not found — proceeding without an
    index-based duplication check") rather than failing or blocking. If an existing row appears to overlap,
    **stop and present that match** (slug, scope, doc path) to the user/agent for confirmation **before**
    defining new epic scope — do not silently proceed past an apparent match.
2. Define epic scope in one sentence (in-scope and out-of-scope).
3. Write Problem, Value, and Acceptance Criteria with measurable language.
4. Build a Features table naming each feature by a **descriptive slug** (kebab-case) — never a positional ID. Each row links to its feature doc path.
5. Add only cross-cutting ADR links in the epic ADR section.
6. Create/update the GitHub epic issue from the epic markdown file (see **GitHub Issue Sync** below).
7. Write the returned issue number into the epic metadata: `| **GitHub Epic** | [#N](https://github.com/...) |`.

## GitHub Issue Sync

Derive the initiative slug from the epic file path: `initiatives/<slug>/epics/...` → `SLUG=<slug>`.

**Issue placement — the v2 tier split:**

| Tier | Home | Why |
|------|------|-----|
| **Epic** (this skill) + **ADRs** | **product-workspace** | the durable governance graph (epics inherit ADRs, span the portfolio); the PM tier |
| **Feature** | **code repo** | the agent's build context (loop clones the code repo, `Closes` same-repo) — see [`feature-generation`](../feature-generation/SKILL.md) |

**Epics live in product-workspace** — even for a dedicated-code-repo initiative. (Monorepo initiatives:
everything in the one repo.) The feature/PR in the code repo references its epic by **absolute**
`<org>/product-workspace#<epic-issue>` — never a relative link (ADR-001 §Consequences). Don't create epic
issues in the code repo.

**Create or update:**

```bash
SLUG=<initiative-slug>              # from initiatives/<slug>/
PW=<org>/product-workspace          # epics live here (the governance repo)
PRIORITY=priority-p1                # from epic metadata
MILESTONE="Phase 1 — Core"          # a GitHub milestone name

gh label create "$SLUG" --description "Initiative: $SLUG" --color 1d76db 2>/dev/null || true

gh issue create --repo "$PW" \
  --title "Epic: <slug> — <title>" \
  --body-file "initiatives/$SLUG/epics/<file>.md" \
  --label epic --label "$SLUG" --label "$PRIORITY" \
  --milestone "$MILESTONE"
```

Because the epic issue lives in the same repo as its doc (product-workspace), the doc's relative links
resolve — `--body-file` on the doc is fine here. (This is the opposite of features, whose issues live in a
*different* repo and therefore need absolute-ref rendering.) Use `--body-file` only — never `--body`.

If the epic issue already exists, update with `gh issue edit <N> --body-file ...` and ensure labels/milestone are set.

Status lives on the GitHub issue and board — do not write a Status field into the epic markdown. **Board entry is native:** the Project's built-in Auto-add (by label) + "Item added → Backlog" place the issue on the board. Just `gh issue create` with the `epic` label — do **not** add the issue to the project via the API (`addProjectV2ItemById`); that bypasses the item-added trigger and lands the card with an empty Status.

## Epic Rules

- Epic is named by a stable **descriptive slug** (e.g. `mcp-transport-core`) — never a positional ID.
- Acceptance criteria are testable and non-ambiguous.
- Features in the table are implementation slices, not goals; each is named by a descriptive slug.
- Epic ADR section must not duplicate feature-specific ADR detail.

## GitHub Source of Truth

- Epic issue body must be updated from the epic markdown file.
- If epic doc and issue differ, reconcile and re-sync immediately.
- Status and dates live on the GitHub issue/board, not in markdown.

## Verification

- [ ] `INDEX.md` read (or its absence noted as a caveat) before defining new epic scope; any apparent
      existing-scope match was surfaced to the user/agent for confirmation before drafting
- [ ] Epic has a descriptive slug and GitHub issue link
- [ ] Problem/Value/ACs are present and measurable
- [ ] Features table names features by descriptive slug and links each feature doc
- [ ] ADRs listed are cross-cutting only
- [ ] GitHub epic issue body matches the markdown file
- [ ] Initiative slug label applied when issues live in the monorepo (`label:<slug>`)
- [ ] Issue created on correct repo (monorepo vs dedicated code repo)
- [ ] No `**Status:**` field written into the epic markdown
