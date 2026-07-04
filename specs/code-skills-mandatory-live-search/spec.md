# Spec: code-skills-mandatory-live-search

> Feature issue: [your-org/kadence#27](https://github.com/your-org/kadence/issues/27)
> Part of epic: [prashanthm/product-workspace#666](https://github.com/prashanthm/product-workspace/issues/666) (`planning-index-and-context-discovery`)

## Behavior

Add a required, mandatory live grep/search step to the two code/test-layer skills —
`skills/implement/SKILL.md` and `skills/test-generation/SKILL.md` — executed **before** writing new
production code or new test code respectively. The step requires the skill to search the live codebase
(grep/glob for the symbol/behavior/module name about to be introduced, across the target repo's current
working tree) and confirm no existing implementation/test already covers the requested behavior before
generating anything new.

This is a prompt-doc feature: the "implementation" is the SKILL.md instruction text itself. There is no
application code or script to write — the same pattern as the sibling `planning-skills-index-lookup`
feature, applied one layer down (code, not planning docs).

### Deliberate contrast with `planning-skills-index-lookup`

`planning-skills-index-lookup` (already merged) wired `feature-generation`/`epic-generation`/`spec-author`
to read the generated `INDEX.md` as a duplication check — appropriate there because planning-layer content
(epics/features) changes slowly enough that a periodically-regenerated index stays useful, and the check is
coarse-grained (epic/feature scale).

This feature is the opposite mechanism, on purpose, per the epic's Why and the epic's own industry research
(Claude Code, Cursor, and GitHub Copilot all use live search or continuously-refreshed indexes for code,
never a periodic CI-cron index for source): code changes on every commit, so a cached index would be stale
by the time it mattered. Both `implement` and `test-generation`'s new required step must therefore be
**explicit** that:

- the search is **live** — executed by grepping/globbing the current working tree at run time, not a
  lookup against a pre-built artifact:
- this live search is **not satisfied by, and is not a substitute for, consulting `INDEX.md`** — even if
  `INDEX.md` exists and was already read (e.g. `implement` reading a feature doc whose parent skills
  already checked the index at planning time), that earlier check does not stand in for this step. The two
  checks operate at different granularities and different layers; doing one does not exempt the other.

### Required step, present in both skills

Each skill's `## Required Workflow` gains an explicit numbered step (inserted immediately before the step
that begins writing new production/test code) that:

1. **Runs a live grep/search** over the target repo's current working tree for the behavior, symbol, or
   module name about to be introduced (function/class names, CLI flags, file/module names, or a
   paraphrase of the behavior itself when no obvious symbol name exists yet). This is a required
   (non-optional) step — not a "may" or "consider" — for every non-trivial addition of new code/tests, the
   same non-optional framing `planning-skills-index-lookup` used for `INDEX.md`.
2. **States explicitly that the search is live** (grep/glob against the working tree at run time, each
   run) and **is independent of / not backed by `INDEX.md`** — a planning-layer index lookup (if any
   already happened upstream) does not substitute for this step.
3. **Surfaces a match before proceeding**: if the live search finds an existing implementation (for
   `implement`) or an existing test (for `test-generation`) that already covers the requested behavior,
   the skill **stops and presents that match** (file path + matching symbol/behavior) to the user/agent for
   confirmation before writing new code — it does not silently proceed to write a duplicate. This mirrors
   the stop-and-surface framing used by `planning-skills-index-lookup`, but the source of the match is a
   live search result, not an index table row.

### Per-skill insertion points

- **`implement`**: `## Required Workflow` currently has step 5 ("Execute in order... implement only files
  listed in the spec's Files section") as the first step that begins writing code, with step 6 ("Implement
  scope only") right after. Insert the live-search step as a new step between step 4 (drafting a spec when
  none exists) and step 5 (execute/write code) — i.e. new step 5, renumbering the rest — so the search runs
  after the spec's Files/Steps are known (so the skill knows what symbol/module it is about to introduce)
  but strictly before any code is written.
- **`test-generation`**: `## Required Workflow` currently has step 4 ("Place tests in paths...") followed
  by step 5 ("Run the test command"). There is no explicit "write the test code" step named as such today
  — step 4 is the first step that implies authoring test files. Insert the live-search step as a new step
  before step 4, so the search runs after the AC/Verification/edge-case mapping (steps 1-3, which tell the
  skill what behavior it's about to test) but before any test file is written.

## Acceptance Criteria

- [ ] AC-1: `implement`'s `SKILL.md` states, as a required (non-optional) workflow step, that it runs a
      live grep/search over the target repo for the behavior/symbol/module it is about to introduce,
      before writing new production code.
- [ ] AC-2: `test-generation`'s `SKILL.md` states the same required step before writing new test code.
- [ ] AC-3: Both skills' required-step wording is explicit that this search is **live** (executed against
      the current working tree each run) and is not satisfied by, or a substitute for, consulting
      `INDEX.md`.
- [ ] AC-4: When the live search finds an existing implementation/test that already covers the requested
      behavior, the skill surfaces that match before proceeding, rather than silently writing a duplicate.
- [ ] AC-5: Verified by a fixture/example run: asking `implement` to build a capability that already exists
      elsewhere in the target repo's code causes the skill to surface the existing code before generating
      new code.

## Out of Scope

- The `INDEX.md` generator or any planning-layer skill (`feature-generation`, `epic-generation`,
  `spec-author`) — already handled by `planning-skills-index-lookup`, a sibling (merged) feature.
- Building any new search tooling/script — the required step uses existing shell primitives (`grep`,
  `rg`, `git grep`, `find`/`glob`) already available in the skill's execution environment; no new script is
  introduced.
- `AGENTS.md` bootstrap/lifecycle wiring — a sibling feature under the same epic.
- Any change to how `implement` or `test-generation` read `specs/<feature>/` or the feature doc — those
  Required Inputs/steps are unchanged; this feature only adds the new pre-write search step.

## ADRs Applied

None — this is a skill-workflow wiring capability (a required live-search step added to two existing skill
docs), not an architectural or system-boundary decision, matching the parent feature issue's ADR section.

## Task Breakdown

> Granular units live in [`tasks.md`](./tasks.md). Because this feature edits prompt text rather than
> application code, each unit's `## Loop AC` verifies the presence and required-ness of specific
> instruction text in the edited `SKILL.md` files (via `grep`), plus the AC-5 fixture walkthrough
> documented as a manual verification record (not machine-checkable — it is a scenario re-run, not a unit
> test).
