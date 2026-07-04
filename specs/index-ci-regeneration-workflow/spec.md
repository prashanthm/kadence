# Spec: index-ci-regeneration-workflow

> Feature issue: [your-org/kadence#23](https://github.com/your-org/kadence/issues/23)
> Part of epic: [prashanthm/product-workspace#666](https://github.com/prashanthm/product-workspace/issues/666) (`planning-index-and-context-discovery`)
> Depends on: `initiative-index-generator` (your-org/kadence#22, merged) — `scripts/generate_initiative_index.py`

## Behavior

A **drift check**, not an auto-fix: CI regenerates `INDEX.md` for each affected initiative into a scratch
location and fails the check if it differs from the committed file. It never commits or pushes a
regenerated file — the contributor is responsible for running the generator locally and committing the
result, same as any other generated-artifact drift gate in this toolkit (e.g. `report_gate.py`'s claimed-
files-vs-diff check).

This is a **reusable/callable workflow** (`workflow_call`), not a workflow with its own `on: push` trigger.
The adopting repo (product-workspace) vendors a thin caller workflow that owns the `on:` trigger + `paths:`
filter and invokes this reusable workflow — mirroring how `templates/.github/workflows/project-status-on-pr.yml`
is vendored today (copy into `<repo>/.github/workflows/`), except this one is `workflow_call`-shaped so one
template file serves every initiative without a copy-pasted job per initiative (AC-3).

### Scoping to affected initiative(s) only (AC-1)

The workflow must not regenerate every initiative on every push — only the initiative(s) whose
`epics/`, `features/`, or `adrs/` subtree actually changed in the pushed commits / PR diff. Two layers of
scoping:

1. **Caller-side `paths:` filter** (adopter's own workflow, documented in SETUP.md, not part of this repo's
   template file): `initiatives/*/{epics,features,adrs}/**` — this is *coarse* scoping, an early-exit at the
   GitHub Actions trigger level so pushes that touch unrelated files never invoke the job at all.
2. **Job-side affected-initiative detection** (this feature, testable): given the set of changed files
   (via `git diff --name-only` against the merge-base/before-SHA — same technique as
   `report_gate.git_changed_files`), extract the distinct `initiatives/<slug>` path prefixes touched under
   `epics/`, `features/`, or `adrs/`. Only those initiatives are regenerated/diffed — a push touching
   `initiatives/foo/epics/x.md` never triggers a diff of `initiatives/bar/INDEX.md`.

This two-layer split means the *reusable* workflow template stays correct even without the caller-side
`paths:` filter (e.g. if invoked on a full-repo push) — it just does no work when the detected initiative
set is empty — but the caller-side filter is still recommended in adopter docs to skip the job entirely on
unrelated pushes (cost/latency, not correctness).

### Affected-initiative detection: `scripts/detect_affected_initiatives.py`

A standalone CLI script (mirrors `generate_initiative_index.py`'s standalone-script style) with one pure,
testable function:

```python
def affected_initiatives(changed_files: list[str]) -> list[str]:
```

- Input: a list of repo-relative changed-file paths (typically the output of
  `git diff --name-only <base>...<head>`).
- Matches paths of the shape `initiatives/<slug>/(epics|features|adrs)/<anything>` (via a compiled regex,
  `^initiatives/([^/]+)/(?:epics|features|adrs)/`). Any path not matching that shape (e.g.
  `initiatives/foo/product-brief.md`, `initiatives/foo/INDEX.md` itself, or a file outside `initiatives/`
  entirely) is ignored — editing `INDEX.md` by hand does not re-trigger a check against itself, and editing
  `product-brief.md`/`initiative.md` does not spuriously regenerate the index (those aren't indexed
  content).
- Returns the **distinct** `initiatives/<slug>` prefixes (e.g. `["initiatives/ai-native-development",
  "initiatives/subsurface-agentic-ai"]`), **sorted** for deterministic output/log order — a push can touch
  more than one initiative in one commit (rare but not disallowed).
- No network calls, no filesystem access — pure string/regex processing over the input list, so it is
  trivially unit-testable without a git checkout.

CLI wrapper:

```
python3 scripts/detect_affected_initiatives.py --changed-files-file <path>
```

or via stdin:

```
git diff --name-only origin/main...HEAD | python3 scripts/detect_affected_initiatives.py
```

Prints one affected `initiatives/<slug>` path per line to stdout (empty output, exit 0, if none match —
"no affected initiatives" is not an error).

### Drift check (AC-2)

For each affected initiative path:

1. If `<initiative-path>/epics/` does not exist, skip with a log line (not a valid initiative directory —
   defensive; `affected_initiatives` already scopes to real initiative-shaped paths, but a moved/deleted
   initiative directory mid-PR should not crash the job).
2. If `<initiative-path>/INDEX.md` does not exist yet, this is the **bootstrap case** (AC-5): log
   `"::notice::<path>/INDEX.md not yet generated — skipping drift check (bootstrap case)"` and continue
   without failing. An initiative that has never had an index generated is not "stale" — there is nothing
   to be stale relative to.
3. Otherwise: copy the initiative directory into a scratch temp dir, run
   `generate_initiative_index.py --initiative-path <scratch-copy>`, then `diff -u` the scratch copy's fresh
   `INDEX.md` against the committed `<initiative-path>/INDEX.md`.
4. A non-empty diff fails the step. The failure message names the stale initiative and file explicitly
   (`::error::initiatives/<slug>/INDEX.md is stale — run 'python3 scripts/generate_initiative_index.py
   --initiative-path initiatives/<slug>' and commit the result`) and echoes the unified diff for
   debuggability.
5. A malformed doc under the affected initiative (the generator's documented `ValueError` cases — missing
   `## What`/`## Status`) surfaces as a job failure with the generator's own error message (uncaught
   exception -> non-zero exit -> failed step); this is a real content defect, not a drift-check bug, so it
   should fail loud exactly like running the generator locally would.

Regenerating into a **scratch copy** (not in place against the checked-out working tree) keeps the job
read-only against the repo checkout — no risk of the diff step itself dirtying the git working tree in a
way that could be mistaken for reviewer-visible changes, and no risk of accidentally committing scratch
output.

### Reusable workflow shape (AC-3)

`templates/.github/workflows/index-regenerate.yml`:

```yaml
on:
  workflow_call:
    inputs:
      python-version:
        type: string
        default: "3.12"
```

No `secrets:` block — the generator makes no network calls and needs no token (matches the depended-on
script's "no network calls" contract). `permissions: contents: read` only (read-only job; no writes, no
Projects/GraphQL calls unlike `project-status-on-pr.yml`).

Job steps:

1. `actions/checkout@v4` — needs enough history for the base-diff (`fetch-depth: 0`, mirroring the
   need to diff against a base ref; a shallow checkout would make `git diff --name-only <base>` unreliable
   for PRs with more than one commit).
2. `actions/setup-python@v5` with `${{ inputs.python-version }}`.
3. Compute changed files: `git diff --name-only ${{ github.event.pull_request.base.sha ||
   github.event.before }}...${{ github.sha }}` (PR event uses `pull_request.base.sha`; push event uses
   `before`; falls back to comparing against `HEAD~1` if neither is set, e.g. workflow_dispatch/first-push
   edge cases — mirrors `report_gate.git_changed_files`'s two-tier fallback).
4. Pipe changed files into `detect_affected_initiatives.py`; capture the affected-initiative list.
5. If the list is empty: log "no initiative epics/features/adrs changed — nothing to check" and exit 0
   (success) immediately — no wasted work.
6. Otherwise, loop over the affected initiatives running the drift check described above; collect failures
   across *all* affected initiatives before failing the job (a push touching two initiatives where only one
   is stale should report both results, not stop at the first).

### Adopter wiring (minimal per-initiative configuration, AC-3)

Because the initiative-detection logic lives in the reusable workflow (not the caller), the adopter's
caller workflow is a few lines regardless of how many initiatives exist — no per-initiative job entries:

```yaml
name: Index Regeneration Check
on:
  pull_request:
    paths: ["initiatives/*/epics/**", "initiatives/*/features/**", "initiatives/*/adrs/**"]
  push:
    branches: [main]
    paths: ["initiatives/*/epics/**", "initiatives/*/features/**", "initiatives/*/adrs/**"]
jobs:
  index-check:
    uses: your-org/kadence/.github/workflows/index-regenerate.yml@main
```

This snippet is documented as an ADOPTER SETUP comment block at the top of the template file (matching
`project-status-on-pr.yml`'s comment-block convention) and is not itself vendored as a separate file in
this feature — copying/adjusting it into product-workspace's `.github/workflows/` is the adopting repo's
own PR (cross-repo adoption pattern, same split as `project-status-on-pr.yml`).

## CLI

```
python3 scripts/detect_affected_initiatives.py [--changed-files-file <path>]
```

- `--changed-files-file` (optional): path to a file with one changed-file path per line. If omitted, reads
  from stdin.
- Prints one affected `initiatives/<slug>` path per line, sorted, to stdout.
- Exit code always 0 (detection never fails — an empty result is valid, not an error).

## Files

- `scripts/detect_affected_initiatives.py` (new) — the affected-initiative detector, stdlib-only (`re`,
  `argparse`, `sys`, `from __future__ import annotations`), following the style of
  `scripts/parse_closing_issues.py` (small focused script, stdin/file dual input, one core pure function
  exported for tests).
- `tests/test_detect_affected_initiatives.py` (new) — pytest, function-based, exercising the core
  `affected_initiatives()` function plus the CLI (stdin + `--changed-files-file`).
- `templates/.github/workflows/index-regenerate.yml` (new) — the reusable `workflow_call` template, heavily
  commented (WHY, not just what), following `project-status-on-pr.yml`'s header-comment + ADOPTER SETUP
  convention.

## Verification

- `python3 -m pytest tests/test_detect_affected_initiatives.py -q`
- `python3 -m pytest tests/ -q` (full suite, no regressions)
- `python3 scripts/doctor.py --strict`
- Manual/documented verification (workflows cannot be unit-tested): exercise the detector script directly
  against a real changed-file list from this repo's own history, and document (in this spec's Verification
  section / PR description) the steps an adopter would take to push a test branch in product-workspace and
  observe the check pass/fail — this is the CI-level equivalent of AC-4's "test PR/fixture exercising both
  paths," executed as a documented manual procedure since this repo does not own product-workspace's CI.

## Edge Cases

- No `INDEX.md` yet for an affected initiative -> bootstrap case, skip (not a failure) — AC-5.
- Changed files touch `initiatives/<slug>/product-brief.md` or `initiatives/<slug>/initiative.md` only (not
  `epics/`, `features/`, or `adrs/`) -> not detected as affected, no regeneration triggered.
- Changed files touch `initiatives/<slug>/INDEX.md` directly (hand-edit) -> not detected as affected by
  `affected_initiatives` itself (the regex only matches `epics|features|adrs` subpaths) — but since the
  epic's generator marks `INDEX.md` as "do not hand-edit," a hand-edited `INDEX.md` with no corresponding
  epics/features/adrs change simply won't be checked by this workflow; that's an acceptable gap (not in
  AC-1..AC-5 scope) since the primary drift source is un-regenerated epic/feature/ADR edits, not
  hand-edited index files.
- Multiple initiatives touched in one push -> both/all checked; failures aggregated, not short-circuited on
  the first.
- Malformed epic/feature/ADR doc in an affected initiative -> generator's own `ValueError` fails the job
  loudly (not swallowed as "just a diff mismatch").
- Changed-files diff comes back empty (e.g. no-op push, or the base ref comparison fails) ->
  `affected_initiatives([])` returns `[]`, workflow exits 0 with the "nothing to check" log line.
