# Tasks: planning-skills-index-lookup

## Task 1 — Edit `feature-generation/SKILL.md`

Replace the epic-scoped `Required Inputs` line with an INDEX.md-first, initiative-wide instruction; add the
INDEX.md read + graceful-degrade + match-surfacing sub-step to workflow step 1; add a Verification line.

### Loop AC

- [x] AC-1: The old narrow line `- Existing features under the same epic` no longer appears in
      `Required Inputs`.
  - verify: `! grep -Fq "Existing features under the same epic" skills/feature-generation/SKILL.md`
- [x] AC-2: `Required Inputs` now references `INDEX.md`.
  - verify: `grep -q "INDEX.md" skills/feature-generation/SKILL.md`
- [x] AC-3: The workflow states the INDEX.md read as required (not optional) before sizing/drafting.
  - verify: `grep -A2 -i "read.*INDEX.md" skills/feature-generation/SKILL.md | grep -qi "required\|before"`
- [x] AC-4: Graceful degradation for a missing `INDEX.md` is stated explicitly.
  - verify: `grep -qi "does not exist\|doesn't exist\|no INDEX.md\|not found" skills/feature-generation/SKILL.md`
- [x] AC-5: Stop-and-surface behavior on an apparent overlap is stated explicitly.
  - verify: `grep -qi "stop and present\|surface that match\|before drafting" skills/feature-generation/SKILL.md`

## Task 2 — Edit `epic-generation/SKILL.md`

Point the existing (already initiative-wide) `Required Inputs` line at `INDEX.md` as the fast path; insert
step 1a in the workflow; add a Verification line.

### Loop AC

- [x] AC-1: `Required Inputs` retains the initiative-wide framing ("same initiative") and now also
      references `INDEX.md`.
  - verify: `grep -q "same initiative" skills/epic-generation/SKILL.md && grep -q "INDEX.md" skills/epic-generation/SKILL.md`
- [x] AC-2: The workflow states the INDEX.md read as required before defining new epic scope.
  - verify: `grep -A2 -i "read.*INDEX.md" skills/epic-generation/SKILL.md | grep -qi "required\|before"`
- [x] AC-3: Graceful degradation for a missing `INDEX.md` is stated explicitly.
  - verify: `grep -qi "does not exist\|doesn't exist\|no INDEX.md\|not found" skills/epic-generation/SKILL.md`
- [x] AC-4: Stop-and-surface behavior on an apparent overlap is stated explicitly.
  - verify: `grep -qi "stop and present\|surface that match\|before drafting" skills/epic-generation/SKILL.md`

## Task 3 — Edit `spec-author/SKILL.md`

Add an `INDEX.md` lookup step (new — this skill had none) before "Author the trio"; add a Verification
line.

### Loop AC

- [x] AC-1: `Required Inputs` references `INDEX.md`.
  - verify: `grep -q "INDEX.md" skills/spec-author/SKILL.md`
- [x] AC-2: A new required workflow step reads `INDEX.md` before drafting `spec.md`/`plan.md`/`tasks.md`
      content, positioned before "Author the trio".
  - verify: `grep -A2 -i "read.*INDEX.md" skills/spec-author/SKILL.md | grep -qi "required\|before"`
- [x] AC-3: Graceful degradation for a missing `INDEX.md` is stated explicitly.
  - verify: `grep -qi "does not exist\|doesn't exist\|no INDEX.md\|not found" skills/spec-author/SKILL.md`
- [x] AC-4: Stop-and-surface behavior on an apparent overlap is stated explicitly.
  - verify: `grep -qi "stop and present\|surface that match\|before drafting" skills/spec-author/SKILL.md`

## Task 4 — Full verification pass

- [x] AC-1: `doctor.py --strict` passes (unaffected by doc-only edits, confirms repo health).
  - verify: `python3 scripts/doctor.py --strict`
- [x] AC-2: Full test suite has no regressions.
  - verify: `python3 -m pytest tests/ -q`

## Task 5 — AC-6 / epic-AC-7 regression walkthrough (manual, documented — not machine-checkable)

Re-run the original incident scenario against the newly-edited `feature-generation/SKILL.md`: an agent
working epic `saa-memory` (`initiatives/subsurface-agentic-ai/epics/saa-memory.md` in the product-workspace
checkout,
which today only has ADR-017/ADR-018 features) is asked to plan/build a memory subsystem. Following the
edited skill's required workflow (read `INDEX.md` first), confirm that a freshly generated
`initiatives/subsurface-agentic-ai/INDEX.md` surfaces `e03-f05-layered-memory` (filed under sibling epic
`saa-runtime`) as a match **before** any new feature is proposed.

- [x] AC-1: A scratch `INDEX.md` is generated for `subsurface-agentic-ai` via
      `python3 scripts/generate_initiative_index.py --initiative-path initiatives/subsurface-agentic-ai`
      (run from product-workspace root; local verification only — never committed to product-workspace).
  - verify: `test -f initiatives/subsurface-agentic-ai/INDEX.md` (from product-workspace root; during the
    walkthrough only; deleted immediately after)
- [x] AC-2: The generated `INDEX.md` Features table contains a row for `e03-f05-layered-memory` with parent
      epic `saa-runtime` and a `Scope` string describing memory/layered-memory behavior.
  - verify: `grep "e03-f05-layered-memory" initiatives/subsurface-agentic-ai/INDEX.md` (from product-workspace root)
- [x] AC-3: Following `feature-generation`'s edited required workflow step-by-step (as documented in the
      report) surfaces that row as a match for the "build a memory subsystem for saa-memory" request before
      proposing new feature content — recorded as a concrete walkthrough transcript in the final report,
      not just asserted.
  - verify: manual — documented in the delivery report (what was read, what row matched, why it counts as
    "before drafting")
- [x] AC-4: The scratch `INDEX.md` is deleted from the product-workspace checkout after the walkthrough.
  - verify: `! test -f initiatives/subsurface-agentic-ai/INDEX.md` (from product-workspace root)
