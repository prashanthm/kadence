# Plan: planning-skills-index-lookup

## Approach

Pure markdown/prompt-doc editing of three existing `SKILL.md` files. No script, no application code, no
new files other than this spec trio. Each edit:

1. Adds/updates a `Required Inputs` line pointing at `INDEX.md`.
2. Inserts a new numbered (or lettered, e.g. `1a`) step in `Required Workflow` that is explicitly
   **required**, describes reading `INDEX.md` at `initiatives/<slug>/INDEX.md`, names the graceful-degrade
   behavior when the file is absent, and names the stop-and-surface behavior on an apparent match.
3. Adds a corresponding line to the skill's `## Verification` checklist so the step is checked off like any
   other required workflow step.

Because "implementation" here is prompt text, correctness is verified by (a) grep-able presence of the
required phrasing in each file, matching the exact required behaviors from the feature issue's ACs, and (b)
a live regression walkthrough (AC-6 / epic AC-7) — dispatching an agent that follows the edited
`feature-generation` SKILL.md against a real initiative (`subsurface-agentic-ai`) and confirming it surfaces
`e03-f05-layered-memory` before proposing new work on `saa-memory`.

## Files

- `skills/feature-generation/SKILL.md` (edit) — replace the epic-scoped `Required Inputs` line; add the
  INDEX.md-first sub-step to workflow step 1; add a Verification line.
- `skills/epic-generation/SKILL.md` (edit) — update `Required Inputs` to point at `INDEX.md` as the fast
  path for the existing initiative-wide requirement; add a new step 1a to workflow; add a Verification line.
- `skills/spec-author/SKILL.md` (edit) — add `INDEX.md` to `Required Inputs`; add a new step 2a to
  workflow, before "Author the trio" (step 3); add a Verification line.
- `specs/planning-skills-index-lookup/{spec,plan,tasks}.md` (new) — this spec trio.

No test files — there is no executable code to unit-test. Verification is grep-based text-presence checks
plus a documented manual regression walkthrough (see tasks.md Task 3).

## Steps

1. **`feature-generation`**:
   - `Required Inputs`: replace `- Existing features under the same epic` with an INDEX.md-first line that
     is initiative-wide in scope (the root-cause fix — the old line's "same epic" framing is exactly what
     missed the sibling-epic match in the original incident).
   - `Required Workflow` step 1 ("Size first..."): prepend a required sub-step — read
     `initiatives/<slug>/INDEX.md` before reasoning about the feature set; if it doesn't exist, proceed with
     a noted caveat; if an existing feature row's `Scope` appears to overlap the requested work, stop and
     present that match before continuing to size/draft.
   - `## Verification`: add a checklist line for the INDEX.md read + match-surfacing.

2. **`epic-generation`**:
   - `Required Inputs`: keep "Related prior epics/features in the same initiative" (already correctly
     scoped) but append that `INDEX.md` is the fast path for satisfying it.
   - `Required Workflow`: insert step 1a between step 1 ("Collect context...") and step 2 ("Define epic
     scope...") — read `INDEX.md`, graceful-degrade if absent, stop-and-surface on apparent overlap in
     either the Epics or Features table.
   - `## Verification`: add a checklist line.

3. **`spec-author`**:
   - `Required Inputs`: add a bullet for `INDEX.md` (the initiative's, for the feature's parent
     epic/initiative).
   - `Required Workflow`: insert step 2a between step 2 ("Confirm Depends On") and step 3 ("Author the
     trio") — read `INDEX.md`, graceful-degrade if absent, stop-and-surface if an existing feature's row
     (other than the one being specced) appears to already cover the spec's intended behavior.
   - `## Verification`: add a checklist line.

4. **Author this spec trio** (`spec.md`, `plan.md`, `tasks.md`) in `specs/planning-skills-index-lookup/`.

5. **Commit and push** on `feat/planning-skills-index-lookup` (already checked out).

6. **Run the AC-6 / epic-AC-7 regression walkthrough** (see tasks.md Task 3) and record the result — this
   is not committed as a repo artifact (it is a verification record for the PR/report), and any scratch
   `INDEX.md` generated in `product-workspace` for the walkthrough is deleted afterward, not committed.

## ADRs

None (matches spec.md ADRs Applied — no ADR dependency).

## Edge Cases

- **`INDEX.md` doesn't exist yet** (bootstrap case: brand-new initiative, or an initiative created before
  this feature shipped, or `initiative-index-generator`/`index-ci-regeneration-workflow` not yet adopted by
  a given repo): every skill proceeds with its existing workflow, stating the caveat rather than blocking.
  This is required by AC-4 — a missing index must never be a hard failure.
- **`INDEX.md` exists but is stale** (source docs changed since last CI regeneration): out of scope for this
  feature — staleness detection/enforcement is `index-ci-regeneration-workflow`'s job (AC-2 of the epic).
  This feature's skills just read whatever `INDEX.md` currently contains; they do not re-generate it or
  validate freshness themselves.
- **Ambiguous "apparent overlap"**: the match-surfacing instruction is deliberately judgment-based ("appears
  to overlap"), not a mechanical string-match rule, per the epic's Problem statement — false negatives (a
  real duplicate not resembling the new work's phrasing) are an inherent limit of the one-line `Scope`
  field, not something this feature can eliminate. The instruction asks the skill to reason about it and err
  toward surfacing, not toward silence.
- **`spec-author` inspecting its own feature's row**: the feature currently being specced will itself have a
  row in `INDEX.md`'s Features table (once features are indexed) — the overlap check is against *other*
  rows, not a false-positive match against itself.
- **Dedicated-code-repo initiatives** (e.g. `subsurface-agentic-ai`): `INDEX.md` still lives in
  product-workspace under `initiatives/<slug>/INDEX.md` even though the skill may be invoked with the code
  repo as working directory (per `spec-author`'s and `implement`'s convention) — the workflow step must
  reference the product-workspace path explicitly, not assume `INDEX.md` is colocated with the code repo.

## Verification

- `grep -n "INDEX.md" skills/feature-generation/SKILL.md skills/epic-generation/SKILL.md skills/spec-author/SKILL.md`
  — each file has at least one required-step reference.
- `python3 scripts/doctor.py --strict`
- `python3 -m pytest tests/ -q` (full suite — unaffected by pure doc edits, confirms no regression)
- Manual: AC-6 regression walkthrough (documented, not automated) — see tasks.md Task 3.
