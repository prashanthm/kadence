# Tasks: index-ci-regeneration-workflow

## Task 1 — `detect_affected_initiatives.py` core + CLI

Implement `affected_initiatives(changed_files: list[str]) -> list[str]` and the `argparse` CLI wrapper
(stdin or `--changed-files-file`) in `scripts/detect_affected_initiatives.py`.

### Loop AC

- [x] AC-1: `affected_initiatives` returns the distinct, sorted `initiatives/<slug>` prefixes for paths
  under `epics/`, `features/`, or `adrs/`, and ignores non-matching paths (e.g. `product-brief.md`,
  `INDEX.md`, files outside `initiatives/`).
  - verify: `python3 -m pytest tests/test_detect_affected_initiatives.py -k affected_initiatives -q`
- [x] AC-2: A push touching two different initiatives' `epics/`/`features/`/`adrs/` returns both, sorted.
  - verify: `python3 -m pytest tests/test_detect_affected_initiatives.py -k multiple -q`
- [x] AC-3: Empty input returns an empty list (not an error).
  - verify: `python3 -m pytest tests/test_detect_affected_initiatives.py -k empty -q`
- [x] AC-4: The CLI reads from stdin by default and from `--changed-files-file` when given, printing one
  affected path per line.
  - verify: `python3 -m pytest tests/test_detect_affected_initiatives.py -k cli -q`

## Task 2 — Reusable CI workflow template

Write `templates/.github/workflows/index-regenerate.yml` as a `workflow_call` reusable workflow: checkout
(`fetch-depth: 0`) -> setup-python -> compute changed files -> detect affected initiatives -> per-initiative
scratch-regenerate-and-diff (skip on missing `INDEX.md`, fail on non-empty diff, aggregate failures) ->
ADOPTER SETUP header comment with the caller-workflow snippet.

### Loop AC

- [x] AC-1: The file has `on: workflow_call:` (not a hardcoded `on: push`), `permissions: contents:
  read`, and no `secrets:` block (stdlib-only sanity check — this toolkit avoids PyYAML by convention,
  see `scripts/loop_events.py`).
  - verify: `python3 -c "c=open('templates/.github/workflows/index-regenerate.yml').read(); assert 'workflow_call:' in c; assert 'contents: read' in c; assert 'secrets:' not in c; print('OK')"`
- [x] AC-2: The workflow pipes `git diff --name-only` output into `detect_affected_initiatives.py` before
  doing any regeneration work (scoped, not full-repo).
  - verify: `grep -q "detect_affected_initiatives.py" templates/.github/workflows/index-regenerate.yml`
- [x] AC-3: The workflow references `generate_initiative_index.py` for the regenerate step and diffs its
  output against the committed `INDEX.md`, with a bootstrap-case skip when `INDEX.md` does not yet exist.
  - verify: `grep -q "generate_initiative_index.py" templates/.github/workflows/index-regenerate.yml && grep -q "not yet generated" templates/.github/workflows/index-regenerate.yml`
- [x] AC-4: An ADOPTER SETUP comment block documents the caller-workflow snippet (`uses:
  your-org/kadence/.github/workflows/index-regenerate.yml@main`).
  - verify: `grep -q "ADOPTER SETUP" templates/.github/workflows/index-regenerate.yml && grep -q "uses: your-org/kadence" templates/.github/workflows/index-regenerate.yml`

## Task 3 — Full verification pass

- [x] AC-1: New test file passes standalone.
  - verify: `python3 -m pytest tests/test_detect_affected_initiatives.py -q`
- [x] AC-2: Full suite has no regressions.
  - verify: `python3 -m pytest tests/ -q`
- [x] AC-3: `doctor.py --strict` passes.
  - verify: `python3 scripts/doctor.py --strict`
- [x] AC-4: Manual sanity check — detector script parses a real changed-file list without error.
  - verify: `cd ~/projects/product-workspace && git log --name-only -5 -- initiatives/ | python3 ~/projects/kadence/scripts/detect_affected_initiatives.py`
