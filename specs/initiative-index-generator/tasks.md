# Tasks: initiative-index-generator

## Task 1 — Parsing helpers + section builders

Implement `extract_first_sentence`, `parse_epic`, `parse_feature`, `parse_adr`, `collect_epics`,
`collect_features`, `collect_adrs` in `scripts/generate_initiative_index.py`.

### Loop AC

- [x] AC-1: `parse_feature` raises `ValueError` (message includes the file path) when the feature doc has
  no `## What` section or an empty one.
  - verify: `python3 -m pytest tests/test_generate_initiative_index.py -k missing_what -q`
- [x] AC-2: `parse_adr` raises `ValueError` when the ADR doc has no `## Status` section or a malformed H1.
  - verify: `python3 -m pytest tests/test_generate_initiative_index.py -k parse_adr_missing -q`
- [x] AC-3: `collect_features`/`collect_adrs` return `[]` for an absent or empty directory (no exception).
  - verify: `python3 -m pytest tests/test_generate_initiative_index.py -k empty_dir -q`

## Task 2 — Rendering + orchestration + CLI

Implement `render_index`, `generate_index`, and the `argparse` `main()` wrapper.

### Loop AC

- [x] AC-1: Given a synthetic initiative dir with epics/features/adrs, `generate_index` writes `INDEX.md`
  with one row per epic/feature/ADR, matching the documented fields.
  - verify: `python3 -m pytest tests/test_generate_initiative_index.py -k full_tree -q`
- [x] AC-2: Running `generate_index` twice on unchanged source produces a byte-identical `INDEX.md`.
  - verify: `python3 -m pytest tests/test_generate_initiative_index.py -k deterministic -q`
- [x] AC-3: The CLI runs end-to-end: `python3 scripts/generate_initiative_index.py --initiative-path <dir>`
  writes `INDEX.md` into `<dir>`.
  - verify: `python3 -m pytest tests/test_generate_initiative_index.py -k cli -q`

## Task 3 — Full verification pass

- [x] AC-1: New test file passes standalone.
  - verify: `python3 -m pytest tests/test_generate_initiative_index.py -q`
- [x] AC-2: Full suite has no regressions.
  - verify: `python3 -m pytest tests/ -q`
- [x] AC-3: `doctor.py --strict` passes (if present at repo root's `scripts/`).
  - verify: `python3 scripts/doctor.py --strict`
