---
name: feature-generation
description: Author intent-only feature docs (What/Why/Acceptance Criteria + parent epic link) from an epic. Engineering detail lives in the code repo's specs/<feature>/, not in the feature doc. Use when deriving new features or refining existing feature docs.
---

# Feature Generation Skill

## Purpose

Create features that capture **intent only** — What, Why, and verifiable Acceptance Criteria — mapped to their parent epic's criteria. A feature doc says *what shippable increment to build and why*; the *how* (files, plan, tasks) lives in the code repo's `specs/<feature>/`, drafted at build time by [`implement`](../implement/SKILL.md). **Each feature is one PR-sized increment — right-sizing happens here at generation (see Sizing), not via a later split step.**

## When to Use

- Deriving features from a new or existing epic
- Refactoring feature docs to a consistent, intent-only format

## Required Inputs

- Parent epic markdown file
- The initiative's `INDEX.md` (`initiatives/<slug>/INDEX.md`) — the required duplication-check fast path;
  see workflow step 1 below. Read the whole initiative's flat feature table, not just the parent epic's —
  the same capability can already exist under a *sibling* epic (this is exactly what a same-epic-only scan
  misses; see Sizing below).
- Relevant ADRs (`adrs/adr-list.md` and ADR files)

## Required Workflow

1. **Size first (the most important step).** Before reasoning about the feature set, **required**: read the
   initiative's `INDEX.md` (`initiatives/<slug>/INDEX.md`, in product-workspace even when this skill is
   invoked with a dedicated code repo as working directory). Scan its flat Features table
   (`Slug | Parent Epic | Scope | Doc`) — across the **whole initiative**, not just the parent epic — for a
   row whose `Scope` appears to already cover the capability about to be sized. If `INDEX.md` does not exist
   yet for this initiative (bootstrap case), **proceed with a noted caveat** ("`INDEX.md` not found —
   proceeding without an index-based duplication check") rather than failing or blocking. If an existing
   row's `Scope` appears to overlap the requested new work, **stop and present that match** (slug, parent
   epic, scope, doc path) to the user/agent for confirmation **before** drafting any new feature content —
   do not silently proceed past an apparent match. Only after this check, decide the *set* of features an
   epic (or a ratified ADR) decomposes into. Reason about scope — do NOT emit one broad feature and defer
   splitting. See **Sizing** below. The output of this step is a list of right-sized feature slugs + a
   dependency order.
2. For each feature: select the epic/ADR criteria it satisfies.
3. Name it with a stable **descriptive slug** (kebab-case) — never a positional ID.
4. Add a `Part of epic: [<epic-slug>](../epics/<epic-slug>.md)` link — this is the hierarchy.
5. Draft What and Why in one short paragraph each.
6. Write 2 to 10 verifiable acceptance criteria tied to the epic/ADR criteria.
7. Add Depends On entries (sibling features / infra / ADRs as needed) — this is the build order.
8. Add feature-specific ADR links (avoid repeating epic-level cross-cutting ADRs unless required).
9. Create/update the GitHub feature issue from the feature markdown file (see **GitHub Issue Sync** below).

**Do not** put an Implementation Plan, files list, or task table in the feature doc — that engineering detail belongs in the code repo's `specs/<feature>/{spec,plan,tasks}.md`. Keep the feature intent-only.

## Sizing (get the granularity right at generation time)

> **Duplication check comes before sizing.** An earlier version of this skill scoped the "does this already
> exist" check to "existing features under the same epic" — too narrow. That framing missed a capability
> that already existed under a *sibling* epic in the same initiative, so it can no longer be relied on as
> the sole check. Required workflow step 1 now reads the **whole initiative's** `INDEX.md` first, precisely
> to catch cross-epic matches before any sizing/drafting begins.

**A feature is one coherent, agent-implementable, PR-sized increment** — the unit that lands as ONE spec
folder (`specs/<slug>/{spec,plan,tasks}.md`) and ONE pull request (`Closes #<feature-issue>`). Sizing is a
**reasoning judgment, not a mechanical rule** — there is no file/line-count tripwire. You are the frontier
model; decompose to the level an agent can implement and verify in a single loop pass, then stop.

Aim for a feature that:
- delivers **one behavior** a reviewer can evaluate in one PR, with a clear pass/fail;
- an agent can **implement and verify in one loop pass** (the `## Loop AC` in its `tasks.md` are all
  behaviorally checkable — tests pass, files exist, lint clean);
- has a **single, coherent seam** — it doesn't bundle two unrelated concerns.

**Split into MULTIPLE features (not one big feature) when:**
- the work spans **two or more independent behaviors** a reviewer would evaluate separately
  (e.g. "route requests" and "handle routing failures" are two features, not one);
- distinct parts touch **disjoint code paths** and could be built/reviewed independently
  (e.g. three domain specialists → three features);
- one part is a **hard dependency** of another (make them separate features with a `Depends On` edge, so
  the loop builds them in order).

**Don't over-split:** a feature should be a *shippable increment*, not a single function. If two slices
must land together to be reviewable/testable, keep them one feature.

When an epic or ADR clearly implies several features, **emit them all** (each its own doc + issue) with a
`Depends On` graph — that graph is the build order. Present the full set for review before creating issues.

**Only derive features from `Accepted` ADRs.** If a feature's core behavior rests on a decision that is
still `Proposed` (check the ADR's `## Status` / the `adr-list.md` row), **do not generate that feature
yet** — it would be speculation on an unratified decision. Instead, leave a deferral marker in the epic's
Relevant-ADRs section: `ADR-NNN (Proposed) — features deferred until Accepted`. When that ADR later flips
to Accepted, `adr-maintenance` step 7a re-runs this skill to derive the net-new features (see
[`adr-maintenance`](../adr-maintenance/SKILL.md)). On a re-run, read the **existing features** first and
emit only what's net-new — never duplicate a feature that already exists.

> There is no `feature-decompose` step in the default path. Right-sizing happens HERE, at generation. Each
> feature's own `tasks.md` (authored at build time by `implement`) holds the granular implementation
> steps + behavioral Loop AC for that one feature — that is the step breakdown *within* a feature, not a
> way to split an oversized feature after the fact.

## GitHub Issue Sync

Derive `SLUG` from the feature path: `initiatives/<slug>/features/...`.

**Where the feature issue lives — the CODE repo (for dedicated-code-repo initiatives).**
The feature issue is **the agent's build context**: the loop clones the code repo, implements there, and its
PR `Closes <code-repo>#<feature>` **same-repo** (so the board self-heals). So create the feature issue in the
**code repo** (`<org>/<code-repo>`), NOT product-workspace. Epics + ADRs stay in product-workspace as the
governance graph and are referenced from the issue by **absolute** ref (see below). For a monorepo initiative
(docs and issues in the same repo), create it there.

> **Never use the raw feature markdown as the issue body across repos.** The feature doc uses
> product-workspace-**relative** links (`../epics/…`, `../adrs/…`) that resolve only inside product-workspace's
> file tree. An issue body is not a repo file, so those links **404** in the code repo. Author the issue body
> as a **rendered** version whose cross-repo references are **ABSOLUTE**: the parent epic as
> `<org>/product-workspace#<epic-issue>`, ADRs/docs as full `https://github.com/<org>/product-workspace/blob/<sha>/…`
> permalinks. No relative `](../…)` link may appear in the issue body (the loop's `report_gate.py` rejects
> one). This is the ADR-001 §Consequences rule: *code-repo issues/PRs reference product-workspace by absolute ref.*
>
> **Pin the permalink to a SHA where the file EXISTS.** A permalink is absolute but still 404s if the
> `<sha>` doesn't contain the file — the classic trap is pinning `main`'s SHA when the docs only live on a
> feature/integration branch (not yet merged). Resolve the SHA from the **branch the docs are actually on**
> (`gh api repos/<org>/product-workspace/branches/<branch> -q .commit.sha`), and **verify each permalink
> resolves** before creating the issue:
> `gh api "repos/<org>/product-workspace/contents/<path>?ref=<sha>" -q .sha` must return a hash, not 404.

```bash
SLUG=<initiative-slug>
CODE_REPO=<org>/<code-repo>          # dedicated code repo (or the monorepo)
EPIC_ISSUE=<org>/product-workspace#<epic-issue-number>   # the parent epic's issue (absolute)
# SHA where the docs live (the branch they're on — NOT main if unmerged):
DOCS_SHA=$(gh api repos/<org>/product-workspace/branches/<docs-branch> -q .commit.sha)

# Author the issue body from the feature doc, but rewrite cross-repo refs to absolute:
#   ../epics/<epic>.md   -> the epic ISSUE ref  ($EPIC_ISSUE)
#   ../adrs/<adr>.md     -> https://github.com/<org>/product-workspace/blob/$DOCS_SHA/…  (verify it resolves)
# Write the rendered body to a temp file, then:
gh issue create --repo "$CODE_REPO" \
  --title "Feature: <slug> — <title>" \
  --body-file <rendered-body>.md \
  --label feature \
  --assignee @me \
  --milestone "<Phase milestone>"
```

After creation, set the feature as a **sub-issue** of its parent epic issue (cross-repo sub-issue relation),
so hierarchy is native, not a link that can rot.

**Always assign the issue to its creator** (`--assignee @me`). The engineering work loop discovers
**assignee-owned** work, so an unassigned issue is invisible to it.

The GitHub board owns Status — a new feature lands in `Backlog` and a human advances it. **Board entry is
native:** the Project's built-in Auto-add (by label) + "Item added → Backlog" place the issue on the board.
Just `gh issue create` with the `feature` label — do **not** add the issue to the project via the API
(`addProjectV2ItemById`); that bypasses the item-added trigger and lands the card with an empty Status. Do
**not** write a `**Status:**` line or a `**GitHub Issue:**` line into the feature markdown; the issue↔doc link
and status live in GitHub.

## Feature Rules

- Every feature maps to at least one explicit epic acceptance criterion.
- Feature scope is a shippable increment, not an umbrella epic.
- The feature doc is **intent only**: What / Why / Acceptance Criteria / Depends On / `Part of epic:` link / feature ADRs. No plan, no files list, no task table, no Status.
- Named by a stable descriptive slug; the slug remains stable after issue creation.
- No placeholder template text is allowed.

## ADR Scope Rules

- Cross-cutting decisions belong at epic level.
- Feature-level design/security/behavior decisions belong in the feature ADR section.
- Link to specific ADR files when available; otherwise link to the ADR index.

## GitHub Source of Truth

- The feature issue body carries the same **intent** (What / Why / AC) as the doc, but with cross-repo
  references **rewritten to absolute** form (`owner/repo#N` / SHA permalinks) — it is a *rendered* copy, not
  the raw relative-linked markdown. Never paste `--body-file <feature-doc>` verbatim into a different repo.
- The durable **markdown doc** (in product-workspace) keeps its relative links — they resolve correctly
  *there*, as files. Only the cross-repo **issue body** uses absolute refs.
- Status and dates live on the GitHub issue/board, not in markdown.

## Verification

- [ ] `INDEX.md` read (or its absence noted as a caveat) before sizing/drafting; any apparent existing-scope
      match was surfaced to the user/agent for confirmation before new feature content was drafted
- [ ] Feature links to parent epic (`Part of epic:`) in the doc, and the ISSUE references the epic by
      absolute `owner/product-workspace#<epic-issue>` (+ sub-issue relation) — no relative link in the body
- [ ] Feature issue created in the **code repo** (dedicated-code-repo initiatives); NOT product-workspace
- [ ] Issue body contains no relative `](../…)` / `](adrs/…)` link (would 404 cross-repo)
- [ ] **Every doc permalink resolves** — each `blob/<sha>/<path>` returns a hash, not 404 (pin the SHA of the branch the docs are on, not `main` if unmerged)
- [ ] Acceptance criteria are verifiable and tied to epic criteria
- [ ] Depends On and ADR sections are present and scoped correctly
- [ ] Feature doc is intent-only — no plan, files list, task table, or Status field
- [ ] Feature issue assigned to its creator (`--assignee @me`)
