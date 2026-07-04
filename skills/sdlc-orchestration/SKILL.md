---
name: sdlc-orchestration
description: Coordinate the lean v2 AI-SDLC delivery flow using Task subagents — product authoring (initiative → brief → epic → feature), the one Ready-for-Dev gate, the autonomous build loop, parallel PR review, and release — with human gates. Use for multi-agent mode or any orchestrated stage of the three-layer flow.
---

# SDLC Orchestration Skill

## Purpose

Route user intent to the correct stage of the **lean three-layer flow**, delegate bounded
work to Task subagents, and fan in results. Humans decide *what* and *whether*; agents
draft the detail and implement; the loop ships draft PRs; humans merge. Status, dates, and
progress live in GitHub — markdown holds only durable intent.

**The flow:** `Initiative → Product Brief → Epic → Feature → [Ready for Dev] → loop implements (specs/<feature>/) → draft PR → review → merge → board Done`.
See [`standard/guide.md`](../../standard/guide.md) for the canonical lifecycle.

## When to Use

- User says "multi-agent mode", names a stage (`feature-batch`, `review-batch`,
  `release-plan`, `brownfield-context`, etc.), or asks for end-to-end delivery
- Batch work with 2+ parallel-safe units (epics, features, review concerns)

## Required Inputs

- Initiative slug under `initiatives/<slug>/`
- The product brief's Epic Index (release order by phase name — the source of order)
- GitHub MCP (optional) — read only; never write issue status

## Stage router

| User intent | `phase` | `stage` | Primary skills |
|-------------|---------|---------|----------------|
| Initiative setup | setup | `setup` | initiative-generation, product-brief-generation |
| Epic batch | delivery | `epic-batch` | epic-generation |
| Feature batch | delivery | `feature-batch` | feature-generation (sizes each feature to one PR-sized increment) |
| Spec draft (optional loop) | build | `spec-loop` | spec-loop → spec-author |
| Build (autonomous loop) | build | `implement-loop` | implement-loop → implement |
| Brownfield context | brownfield | `brownfield-context` | context-acquisition |
| Brownfield assess | brownfield | `brownfield-assess` | current-state-assessment |
| Brownfield extract | brownfield | `brownfield-adr/epic/feature` | adr-recovery, epic-extraction, feature-extraction |
| Migration forward | brownfield | `migration-plan` etc. | migration-planning, parity-baseline, decommission-planning |
| ADR catalog | foundation | `foundation-adr-list` | adr-list-generation |
| Foundation ADRs | foundation | `foundation-adr-tier1/2/3` | adr-maintenance |
| Architecture docs | foundation | `foundation-arch` | architecture-documentation |
| Foundation gate | foundation | `foundation-review` | foundation-review |
| CI triage | build | `ci-triage` | ci-triage |
| Open PR | build | `pr-open` | pull-request template (the loop opens it) |
| PR reviews | review | `review-batch` | pr-review, security-review, quality-review, observability-review, pr-traceability |
| Release scope | release | `release-plan` | release-scope-planning |
| Integration plan | release | `integration-plan` | integration-test-plan |
| Release notes | release | `release-notes` | release-notes-generation |
| Release gate review | release | `release-review-batch` | quality / security / observability / pr-traceability / release-metadata review (parallel readonly) |
| Release approval | release | `release-approval` | release-approval |
| Release tag | release | `release-tag` | release-publication (preflight-gated crane-copy) |
| Release closeout (brownfield) | release | `release-closeout` | release-closeout |
| Runbooks | ops | `runbook-batch` | runbook-generation |
| Parity cutover | brownfield | `parity-verify` | parity-verify |

## Activity types → Task

| Activity type | Task | Readonly |
|---------------|------|----------|
| GatherContext | `explore` | yes |
| Author*, Decompose, Plan, Implement, AuthorTests, PlanRelease, AuthorReleaseNotes, PlanIntegrationTest, AuthorRunbook | `generalPurpose` | no |
| RunVerification, CI | `shell` | no |
| Review* | `generalPurpose` | yes |
| VerifyParity | `generalPurpose` | yes |

**Hard rule:** Use the Task tool for all subagent work. Never role-play in parent chat.

## Required Workflow

### 1. Product authoring (human-led)

Sequential Author Tasks with a human gate between each:

1. **Initiative** — [`initiative-generation`](../initiative-generation/SKILL.md).
2. **Product Brief** — [`product-brief-generation`](../product-brief-generation/SKILL.md);
   the Epic Index defines release order (phase names, no dates).
3. **Epics** — parallel [`epic-generation`](../epic-generation/SKILL.md) Tasks, one output
   path each. `run_in_background: true` if ≥ 3. Each epic → a GitHub Epic issue on a
   milestone/phase.
4. **Features** — parallel [`feature-generation`](../feature-generation/SKILL.md) Tasks; each
   feature carries What / Why / Acceptance Criteria and a `Part of epic:` link, and becomes a
   GitHub Feature issue.

### 2. The gate(s) — Ready for Dev (+ optional Ready for Spec)

A human reviews a feature and moves its card to **`Ready for Dev`**. **Nothing is built before
this.** The orchestrator never sets this itself; ask the human if the state is unclear.

**Optional spec-review gate.** A team that wants to review the *plan* before code adds a
**`Ready for Spec`** column and runs the **spec-loop**. Flow: human → `Ready for Spec` →
spec-loop ([`spec-author`](../spec-author/SKILL.md)) authors `specs/<slug>/{spec,plan,tasks}.md`
and opens a **spec-only** draft PR (`spec/<n>-<slug>`, `Refs #`) → engineer merges it → card
**auto-promotes** to `Ready for Dev` → implement-loop takes over. Opt-in; simple features skip it.

### 3. Build — the autonomous loop family (kloop)

The **implement-loop** (build member of the [kloop](../engineering-work-loop/SKILL.md)
family) picks up `Ready for Dev` issues and, per feature, works in an isolated git worktree via
[`implement`](../implement/SKILL.md): it authors (or reads, if spec-loop already wrote it) the code-repo
**spec folder** `specs/<feature>/{spec,plan,tasks}.md`, implements, re-runs every Loop AC `verify:` itself
(the agent's `[x]` is advisory), and opens a **draft** code PR (`Closes #<feature-issue>`) with a Work Fix
Report gated by `report_gate.py`. Unless the optional `Ready for Spec` gate is used, the spec lives in the PR.

**Right-sizing happens at generation, not build:** [`feature-generation`](../feature-generation/SKILL.md)
emits each feature as one coherent, PR-sized increment (splitting a big capability into several features
with a `Depends On` graph). There is no build-time decompose step; `implement` authors `tasks.md` as the
ordered/`[P]` step breakdown *within* one already-right-sized feature.

### 4. review-batch (parallel concerns)

Launch readonly Tasks in one turn — one per concern. The reviewable artifact is the PR diff:

| Concern | Skill | Output |
|---------|-------|--------|
| code | [`pr-review`](../pr-review/SKILL.md) | `.sdlc/reviews/<pr>-code.md` |
| security | [`security-review`](../security-review/SKILL.md) | `.sdlc/reviews/<pr>-security.md` |
| quality | [`quality-review`](../quality-review/SKILL.md) | `.sdlc/reviews/<pr>-quality.md` |
| observability | [`observability-review`](../observability-review/SKILL.md) | `.sdlc/reviews/<pr>-observability.md` |
| traceability | [`pr-traceability`](../pr-traceability/SKILL.md) | `.sdlc/reviews/<pr>-traceability.md` |

Present a combined review summary. Request human merge approval — **never merge** (unless
risk-based auto-land is explicitly enabled, default OFF).

### 5. Foundation stages

**foundation-adr-tier*** — parallel [`adr-maintenance`](../adr-maintenance/SKILL.md) Tasks per
ADR file. **foundation-arch** — parallel
[`architecture-documentation`](../architecture-documentation/SKILL.md) sections.
**foundation-review** — single readonly [`foundation-review`](../foundation-review/SKILL.md) Task.

### 6. Release stages

**release-plan** → **integration-plan** → **release-notes** → **release-review-batch** →
**release-approval** → **release-tag** (sequential, with PO/Builder approval gates between).
**integration-run** — shell Task executes the plan (a human may run it manually).

### 7. Brownfield stages

Run reverse skills **in order**: `brownfield-context` → `brownfield-assess` →
`brownfield-adr` → `brownfield-epic` → `brownfield-feature`. Within a stage, parallelize per
artifact (same as epic-batch). Forward: migration-plan → parity-baseline → decommission-plan
(sequential); `parity-verify` before cutover.

### 8. Fan-in validation

- No duplicate output paths
- All Task outputs recorded and referenced
- Review reports present before the merge prompt
- Failed tasks have an `error` set

## Invocation examples

```
Generate all epics from the product brief in multi-agent mode
Generate all features for epic <epic-slug> in multi-agent mode
Move feature <feature-slug> to Ready for Dev, then run the build loop
Run review-batch for PR #123 — all concerns in parallel
Run release-plan for Phase 1 then release-notes
Run brownfield-context for assessments/edi-express/
```

## Anti-Patterns

- Monolithic PR review Task — always decompose by concern
- Building a feature before it is `Ready for Dev`
- Reintroducing a task-list / spec-authoring / spec-approval gate — the spec lives in the PR
- Merging or advancing GitHub status without a human
- Treating markdown as the source of status or order (GitHub owns status; the Epic Index owns order)

## Verification

- [ ] Stage matches the lean three-layer flow
- [ ] Nothing built before `Ready for Dev`
- [ ] Parallel batches use multiple Tasks per turn where required
- [ ] review-batch produced its concern reports
- [ ] Gates prompted, not auto-passed
