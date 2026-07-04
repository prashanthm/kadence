# Plan: code-skills-mandatory-live-search

## Approach

Pure markdown/prompt-doc editing of two existing `SKILL.md` files. No script, no application code, no new
files other than this spec trio. Each edit:

1. Inserts a new numbered required workflow step (before the step that begins writing new code/tests) that
   names the live grep/search as mandatory.
2. States explicitly that the search is **live** (executed against the current working tree each run) and
   is **not** backed by, and does not substitute for, `INDEX.md`.
3. States the stop-and-surface behavior: an existing match must be presented before any new code/test is
   written.
4. Adds a corresponding line to the skill's `## Verification` checklist.

Because "implementation" here is prompt text, correctness is verified by (a) grep-able presence of the
required phrasing in each file, matching the exact required behaviors from the feature issue's ACs, and (b)
a fixture/example walkthrough (AC-5) — following the newly-edited `implement` `SKILL.md`'s required
live-search step against a real, already-existing capability in this repo's own `scripts/` and confirming
it would be surfaced before drafting anything new.

## Files

- `skills/implement/SKILL.md` (edit) — insert the live-search step into `## Required Workflow` (new step
  5, renumbering steps 5-11 to 6-12); add a `## Verification` line.
- `skills/test-generation/SKILL.md` (edit) — insert the live-search step into `## Required Workflow` (new
  step 4, renumbering steps 4-6 to 5-7); add a `## Verification` line.
- `specs/code-skills-mandatory-live-search/{spec,plan,tasks}.md` (new) — this spec trio.

No test files — there is no executable code to unit-test. Verification is grep-based text-presence checks
plus a documented fixture walkthrough (see tasks.md Task 3).

## Steps

1. **`implement`**:
   - `## Required Workflow`: insert a new step between the current step 4 ("If no spec exists and work is
     non-trivial — draft `specs/<feature>/spec.md`...") and step 5 ("Execute in order..."). New step reads
     (numbered 5, pushing old 5-11 to 6-12): run a live grep/search over the target repo for the
     behavior/symbol/module about to be introduced; state explicitly this is a live, working-tree search,
     independent of `INDEX.md`; if an existing implementation is found that already covers the requested
     behavior, stop and present that match before writing new code.
   - `## Verification`: add a checklist line for the live-search step.

2. **`test-generation`**:
   - `## Required Workflow`: insert a new step between the current step 3 ("Add negative-path tests for
     documented edge cases.") and step 4 ("Place tests in paths declared in the spec's Files section or
     repo convention."). New step reads (numbered 4, pushing old 4-6 to 5-7): run a live grep/search over
     the target repo for existing tests covering the behavior about to be tested; state explicitly this is
     a live, working-tree search, independent of `INDEX.md`; if an existing test is found that already
     covers the requested behavior, stop and present that match before writing new test code.
   - `## Verification`: add a checklist line.

3. **Author this spec trio** (`spec.md`, `plan.md`, `tasks.md`) in
   `specs/code-skills-mandatory-live-search/`.

4. **Commit and push** on `feat/code-skills-mandatory-live-search` (already checked out in this worktree).

5. **Run the AC-5 fixture walkthrough** (see tasks.md Task 3) and record the result in the delivery
   report — this is not a repo artifact, it is a documented verification record.

## ADRs

None (matches spec.md ADRs Applied — no ADR dependency).

## Edge Cases

- **No obvious symbol name yet** (the behavior is being introduced fresh, with no established
  function/class/CLI-flag name to grep for): the required step still applies — search on the closest
  available terms (a paraphrase of the behavior, related domain nouns, file/module naming conventions used
  elsewhere in the repo) rather than being skipped for lack of an exact symbol.
- **Search tool availability**: the step uses whatever search primitive is available in the execution
  environment (`rg`/`grep`/`git grep`/glob via `find` or the agent's native search tool) — it does not
  mandate a specific tool, since `implement`/`test-generation` run in different environments (local CLI,
  engineering-work-loop worktree, orchestrated multi-agent mode).
- **`INDEX.md` already consulted upstream**: if a planning-layer skill (e.g. `feature-generation`) already
  read `INDEX.md` when the feature was drafted, that earlier index check does not exempt `implement` or
  `test-generation` from this live search — the two checks are at different layers/granularities and are
  independent per the epic's Why (this is the point AC-3 tests for).
- **Match found but not actually a duplicate** (a false-positive symbol-name collision, e.g. same function
  name but different behavior): the stop-and-surface step asks the skill to present the match for
  confirmation, not to auto-abort — a human/agent can confirm it's not a real duplicate and proceed. This
  mirrors `planning-skills-index-lookup`'s "err toward surfacing, not toward silence" framing.
- **Trivial additions** (e.g. adding a single well-scoped helper the spec's Files section already commits
  to, or a one-line change to an existing function): the step still applies — "trivial" is not an
  exemption clause in the required-step wording, unlike `implement`'s existing step 4 (spec-drafting)
  which is explicitly gated on "non-trivial" work. The live-search step has no such gate, since a
  duplicate-behavior check is cheap regardless of change size.

## Verification

- `grep -n "live" skills/implement/SKILL.md skills/test-generation/SKILL.md` — each file names the search
  as live.
- `grep -n "INDEX.md" skills/implement/SKILL.md skills/test-generation/SKILL.md` — each file explicitly
  distinguishes the live search from `INDEX.md`.
- `python3 scripts/doctor.py --strict`
- `python3 -m pytest tests/ -q` (full suite — unaffected by pure doc edits, confirms no regression)
- Manual: AC-5 fixture walkthrough (documented, not automated) — see tasks.md Task 3.
