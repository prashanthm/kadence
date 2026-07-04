---
name: test-generation
description: Author unit and integration tests for a feature and its implementation. Use after implement or in parallel when test paths are disjoint.
---

# Test Generation Skill

## Purpose

Add tests that cover the feature's acceptance criteria, the Verification and Edge Cases in
the code repo's `specs/<feature>/`, and negative paths — asserting against the implemented
code, not a separate spec-approval gate.

## When to Use

- After `implement` produces the feature's changes
- Orchestrator `test-batch` stage
- Parallel with implement only when test paths do not overlap src edits in flight

## Required Inputs

- The feature doc (What / Why / Acceptance Criteria)
- The code repo `specs/<feature>/{spec,plan,tasks}.md` (Verification + Edge Cases)
- Changed files list from the implementation

## Required Workflow

1. Map each feature acceptance criterion to at least one test.
2. Map each `specs/<feature>/` Verification item to at least one test.
3. Add negative-path tests for documented edge cases.
4. **Run a live grep/search before writing new test code — required, not optional.** For each behavior the mapped AC/Verification items are about to be tested, search the target repo's **current working tree** (`grep`/`rg`/`git grep`/glob, or the agent's native code-search tool — no exact symbol name yet is not an exemption, search on the closest available terms) for an existing test that already covers it. This search is **live** — executed against the working tree fresh, every run — and is **independent of, not backed by, and not satisfied by consulting `INDEX.md`**: `INDEX.md` is a planning-layer, epic/feature-scale artifact that goes stale between commits; this step is a code-scale, this-instant check, and doing one never exempts the other. **If the search finds an existing test that already covers the requested behavior, stop and present that match (file path + matching test/assertion) before writing anything new** — do not silently proceed to write a duplicate test.
5. Place tests in paths declared in the spec's Files section or repo convention.
6. Run the test command; report pass/fail.
7. Do not change production code except test hooks the implementation requires.

## Multi-Agent Delegation

| Field | Value |
|-------|-------|
| Parallel-safe | Yes — disjoint test file paths |
| Stage | `test-batch` |
| Activity type | AuthorTests |
| Return payload | `{ test_files: [], test_results: pass|fail }` |

## Verification

- [ ] Every feature acceptance criterion has test coverage
- [ ] Every spec Verification item has test coverage
- [ ] Negative paths included where specified
- [ ] Live grep/search run over the working tree for each behavior about to be tested, before writing new test code; any existing test match surfaced and confirmed, not silently duplicated
- [ ] Tests executed with result reported
