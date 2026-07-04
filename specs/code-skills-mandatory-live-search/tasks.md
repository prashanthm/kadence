# Tasks: code-skills-mandatory-live-search

## Task 1 — Edit `implement/SKILL.md`

Insert the required live-search step into `## Required Workflow` before the code-writing step; add a
`## Verification` line.

### Loop AC

- [x] AC-1: The workflow contains a required step to run a live grep/search over the target repo for the
      behavior/symbol/module about to be introduced, before writing new production code.
  - verify: `grep -qi "live grep\|live search" skills/implement/SKILL.md`
- [x] AC-2: The step is stated as required (not optional).
  - verify: `grep -B2 -A2 -i "live grep\|live search" skills/implement/SKILL.md | grep -qi "required\|mandatory"`
- [x] AC-3: The step is explicit that the search runs against the current working tree each run and is not
      backed by / not a substitute for `INDEX.md`.
  - verify: `grep -qi "not.*INDEX.md\|independent of.*INDEX.md\|not backed by.*INDEX.md" skills/implement/SKILL.md`
- [x] AC-4: The step states the match-surfacing behavior — an existing implementation covering the
      requested behavior must be surfaced before writing new code, not silently duplicated.
  - verify: `grep -qi "stop and present\|surface that match\|before writing" skills/implement/SKILL.md`
- [x] AC-5: `## Verification` gains a checklist line for the live-search step.
  - verify: `grep -A20 "^## Verification" skills/implement/SKILL.md | grep -qi "live"`

## Task 2 — Edit `test-generation/SKILL.md`

Insert the same required live-search step into `## Required Workflow` before the test-writing step; add a
`## Verification` line.

### Loop AC

- [x] AC-1: The workflow contains a required step to run a live grep/search over the target repo for
      existing tests covering the behavior about to be tested, before writing new test code.
  - verify: `grep -qi "live grep\|live search" skills/test-generation/SKILL.md`
- [x] AC-2: The step is stated as required (not optional).
  - verify: `grep -B2 -A2 -i "live grep\|live search" skills/test-generation/SKILL.md | grep -qi "required\|mandatory"`
- [x] AC-3: The step is explicit that the search runs against the current working tree each run and is not
      backed by / not a substitute for `INDEX.md`.
  - verify: `grep -qi "not.*INDEX.md\|independent of.*INDEX.md\|not backed by.*INDEX.md" skills/test-generation/SKILL.md`
- [x] AC-4: The step states the match-surfacing behavior — an existing test covering the requested
      behavior must be surfaced before writing new test code, not silently duplicated.
  - verify: `grep -qi "stop and present\|surface that match\|before writing" skills/test-generation/SKILL.md`
- [x] AC-5: `## Verification` gains a checklist line for the live-search step.
  - verify: `grep -A20 "^## Verification" skills/test-generation/SKILL.md | grep -qi "live"`

## Task 3 — AC-5 fixture walkthrough (manual, documented — not machine-checkable)

Pick a real, already-existing capability in this repo's own `scripts/` and simulate being asked to
"implement a script that does X" where X already exists, following the newly-edited `implement/SKILL.md`'s
required live-search step verbatim. Confirm the existing code is actually found and surfaced before any new
code is drafted.

Fixture: `scripts/detect_affected_initiatives.py` — a pure function `affected_initiatives(changed_files:
list[str]) -> list[str]` that parses a list of changed repo-relative file paths and returns the distinct,
sorted `initiatives/<slug>` prefixes touched under `epics/`, `features/`, or `adrs/`, plus a CLI wrapper
(`main()`) that reads paths from stdin or `--changed-files-file` and prints matches one per line.

Simulated ask: "Implement a script that reads a list of changed file paths and prints which
`initiatives/<slug>` directories were affected, so we can scope an index-regeneration check to only the
touched initiatives."

- [x] AC-1: Following `implement`'s edited required workflow step, a live grep/search is run over
      `scripts/` for terms matching the requested behavior (e.g. `affected`, `initiative`, `changed.file`,
      `detect`) before any new file is drafted.
  - verify: manual — documented in the delivery report as the exact search command(s) run and their raw
    output.
- [x] AC-2: The search surfaces `scripts/detect_affected_initiatives.py` as an existing match for the
      requested behavior.
  - verify: `grep -l "affected_initiatives\|initiatives/<slug>" scripts/detect_affected_initiatives.py`
- [x] AC-3: The walkthrough confirms the surfacing happens **before** any new script/code would be drafted
      — i.e. the match is presented for confirmation as the very next step after the search, not after
      code has already been written.
  - verify: manual — documented in the delivery report as a step-by-step trace against the edited
    `SKILL.md` text (which step number the search is, which step would have been "write new code", and
    that the surfaced match interrupts that sequence).
- [x] AC-4: The report states the conclusion explicitly: implementing a new script for this request would
      be a duplicate of `detect_affected_initiatives.py`, and the correct action per the edited skill is to
      present that file (not draft a new one) and ask whether to extend/reuse it instead.
  - verify: manual — documented in the delivery report.

## Task 4 — Full verification pass

- [x] AC-1: `doctor.py --strict` passes (unaffected by doc-only edits, confirms repo health).
  - verify: `python3 scripts/doctor.py --strict`
- [x] AC-2: Full test suite has no regressions.
  - verify: `python3 -m pytest tests/ -q`
