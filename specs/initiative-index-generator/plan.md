# Plan: initiative-index-generator

## Approach

Single-file stdlib script, mirroring `discover_engineering_work_candidates.py` conventions: module
docstring, `from __future__ import annotations`, small pure functions (parse-one-file, format-one-row)
composed by an orchestrating `generate_index()` function, then a thin `main()`/`argparse` CLI wrapper.
Pure functions are unit-tested directly (no subprocess/CLI invocation needed in tests); one or two
integration-style tests drive the CLI end-to-end via `main()`/`generate_index()` against a `tmp_path`
initiative tree.

## Files

- `scripts/generate_initiative_index.py` (new)
- `tests/test_generate_initiative_index.py` (new)

## Steps

1. **Parsing helpers** (pure functions, each independently testable):
   - `parse_epic(path: Path) -> dict` — slug (filename stem), phase (Metadata table row, else header-line
     regex, else `"Unknown"`), doc path.
   - `parse_feature(path: Path) -> dict` — slug (filename stem), parent epic (from `> Part of epic:` line,
     else `"Unknown"`), scope (from `## What` section — raises `ValueError` if section missing or empty),
     doc path.
   - `parse_adr(path: Path) -> dict` — number + title (from `# ADR-NNN: Title` heading, raises `ValueError`
     if missing/malformed), status (first non-blank line after `## Status`, raises `ValueError` if section
     missing), doc path.
   - `extract_first_sentence(text: str) -> str` — the shared one-line-summary heuristic (first `.` followed
     by whitespace/EOF; strips `**bold**` markers and collapses whitespace).

2. **Section builders**:
   - `collect_epics(epics_dir: Path) -> list[dict]` — sorted by slug.
   - `collect_features(features_dir: Path) -> list[dict]` — sorted by slug.
   - `collect_adrs(adrs_dir: Path) -> list[dict]` — filters to `adr-\d+-*.md` (excludes `adr-list.md`),
     sorted by numeric ADR number.
   - Each returns `[]` when the directory is absent or empty — no error.

3. **Rendering**:
   - `render_index(initiative_slug: str, epics, features, adrs) -> str` — builds the three markdown tables
     as a single string. No timestamps or non-deterministic content. Deterministic column widths are not
     required (plain `| a | b |` rows, not padded/aligned — simpler and still valid markdown, avoids
     width-calculation complexity that's irrelevant to the AC).

4. **Orchestration**:
   - `generate_index(initiative_path: Path) -> str` — validates `epics/` dir exists (else `ValueError`
     "not a valid initiative directory"), calls the three collectors, calls `render_index`, writes
     `INDEX.md` in `initiative_path`, returns the written content (return value makes the byte-identical
     property directly testable without a second file read in tests, though tests also verify by re-running
     and diffing the file for extra confidence).

5. **CLI**: `argparse` with `--initiative-path` (required), calls `generate_index(Path(args.initiative_path))`.

## ADRs

None — this feature has no ADR dependency (confirmed in the feature issue: "None — this is a tooling
capability").

## Edge Cases (see spec.md for full list)

- Missing `## What` / missing `## Status` / malformed ADR heading -> `ValueError`, propagates uncaught to
  a non-zero exit (matches sibling scripts' convention — no try/except wrapper in `main()`).
- Empty/absent `features/`/`adrs/` dirs -> empty list, not an error.
- Determinism -> stable sort keys, no `datetime.now()`/timestamps anywhere in the output.

## Verification

- `python3 -m pytest tests/test_generate_initiative_index.py -q`
- `python3 -m pytest tests/ -q`
- `python3 scripts/doctor.py --strict`
