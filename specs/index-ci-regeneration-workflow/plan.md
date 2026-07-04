# Plan: index-ci-regeneration-workflow

> Feature issue: [your-org/kadence#23](https://github.com/your-org/kadence/issues/23)

## Approach

Two deliverables, split so the non-trivial logic is testable Python and the workflow YAML stays thin glue
around it (per the epic's AC-1 "scoped to the affected initiative(s) only" requirement, which needs real
"which initiative(s) changed" logic — worth a script, not embedded shell):

1. **`scripts/detect_affected_initiatives.py`** — pure function `affected_initiatives(changed_files:
   list[str]) -> list[str]` plus a thin CLI wrapper (stdin or `--changed-files-file`). No filesystem/network
   access — takes a list of path strings, returns a sorted list of matched `initiatives/<slug>` prefixes.
   This is the part that gets full pytest coverage.
2. **`templates/.github/workflows/index-regenerate.yml`** — `workflow_call` reusable workflow: checkout ->
   setup-python -> compute changed files via `git diff --name-only` -> pipe into the detector script ->
   for each affected initiative, scratch-regenerate + diff against committed `INDEX.md` (skip if no
   `INDEX.md` yet) -> fail with a clear per-initiative message on drift. Heavily commented like
   `project-status-on-pr.yml`, with an ADOPTER SETUP block documenting the caller-workflow snippet
   (not vendored as a separate file — that's product-workspace's own adoption PR).

No ADRs — the epic and feature docs both say this is a CI/tooling capability, not an architectural
decision.

## Why a drift check, not auto-commit

The epic's plan-stage framing (referenced in the session's own prior planning) considered an
auto-committing regeneration workflow, but the **ratified feature issue's AC-2 wording is explicit**:
"regenerates `INDEX.md` in a scratch location and diffs it against the committed file... a non-empty diff
fails the check." That is a fail-on-stale gate, not a write-back. Corroborating evidence in the issue text
itself: "the same drift-check pattern already used elsewhere in the toolkit (e.g. report-gate checks)" —
`scripts/report_gate.py` is a read-only gate (`git_changed_files` + comparison, never a commit). The AC-4
verification story ("a PR that edits ... without regenerating ... fails CI; the same PR with a regenerated
`INDEX.md` passes") also only makes sense for a fail/pass gate — an auto-commit workflow wouldn't need a
"regenerate it yourself and it passes" verification path, it would just fix the file itself. Building to
the actual AC text over the earlier planning-stage assumption.

## Files

- `scripts/detect_affected_initiatives.py` (new)
- `tests/test_detect_affected_initiatives.py` (new)
- `templates/.github/workflows/index-regenerate.yml` (new)

No changes to `scripts/generate_initiative_index.py` (consumed as-is, per its documented CLI/exit-code
contract) or to any existing skill docs — this feature is CI plumbing only.

## Steps

1. Write `detect_affected_initiatives.py`: regex-match `initiatives/<slug>/(epics|features|adrs)/...`,
   collect distinct sorted `initiatives/<slug>` prefixes, CLI wrapper reading stdin or
   `--changed-files-file`.
2. Write `tests/test_detect_affected_initiatives.py`: unit tests for the pure function (single match, no
   match, multiple initiatives, `INDEX.md`/`product-brief.md` non-matches, empty input) plus CLI-level
   tests (stdin path, `--changed-files-file` path) via `subprocess.run`.
3. Write `templates/.github/workflows/index-regenerate.yml`: `workflow_call` trigger, `contents: read`
   permission, checkout with `fetch-depth: 0`, setup-python, changed-files computation with PR/push/fallback
   branches, detector invocation, per-initiative scratch-regenerate-and-diff loop with bootstrap-skip and
   aggregated failure reporting, ADOPTER SETUP header comment block with the caller-workflow snippet.
4. Run the full verification pass (new test file standalone, full suite, `doctor.py --strict`).
5. Manual verification: run the detector script against this repo's own recent commit range as a sanity
   check that real changed-file lists parse as expected (documented in the spec's Verification section and
   in the final report — no live GitHub Actions run is possible from this repo alone since the trigger
   paths are product-workspace's `initiatives/` tree, not this repo's).

## Edge Cases (see spec.md for full detail)

- Bootstrap case (no `INDEX.md` yet) -> skip, not fail (AC-5).
- Multiple initiatives touched in one push -> all checked, failures aggregated.
- Malformed doc under an affected initiative -> generator's `ValueError` propagates as a real job failure.
- Non-epics/features/adrs paths under `initiatives/<slug>/` (e.g. `product-brief.md`, `INDEX.md` itself) ->
  not detected as affected.

## Verification

- `python3 -m pytest tests/test_detect_affected_initiatives.py -q`
- `python3 -m pytest tests/ -q`
- `python3 scripts/doctor.py --strict`
- Manual: run `git log --name-only` over recent commits touching `initiatives/` in product-workspace,
  pipe through `detect_affected_initiatives.py`, confirm sane output.
