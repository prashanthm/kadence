# Spec: initiative-index-generator

> Feature issue: [your-org/kadence#22](https://github.com/your-org/kadence/issues/22)
> Part of epic: [prashanthm/product-workspace#666](https://github.com/prashanthm/product-workspace/issues/666) (`planning-index-and-context-discovery`)

## Behavior

A standalone CLI script, `scripts/generate_initiative_index.py`, that reads one initiative directory
(`initiatives/<slug>/`) and writes a deterministic `INDEX.md` into that same directory.

`INDEX.md` has three sections, each a markdown table:

1. **Epics** — one row per `epics/*.md` file: slug, phase, doc path (relative to the initiative dir).
2. **Features** — one flat row per `features/*.md` file: slug, parent epic slug, one-line scope, doc path.
3. **ADRs** — one row per `adrs/adr-*.md` file (excluding `adr-list.md`): number, title, doc path, status.

Rows within each table are sorted by a stable key (slug for epics/features, numeric ADR number for ADRs)
so two runs against unchanged source produce a byte-identical file — no timestamps, no directory-listing-order
dependence.

### Source field extraction

- **Epic slug**: the epic filename stem (e.g. `saa-memory.md` -> `saa-memory`). Cross-checked against the
  `| **Slug** |` row in the `## Metadata` table when present; the filename stem is the fallback/primary key
  either way since it is always present.
- **Epic phase**: the `| **Phase** |` row in the `## Metadata` table (e.g. `Phase 2`). If absent, falls back
  to parsing `Phase N` out of the `> Epic slug: ... Phase N.` header line. If neither is present, phase is
  the literal string `Unknown` (never blank, never an error — phase is best-effort metadata, not a
  correctness-critical field).
- **Feature slug**: the feature filename stem (e.g. `e03-f05-layered-memory.md` -> `e03-f05-layered-memory`).
- **Feature parent epic**: parsed from the `> Part of epic: [slug](../epics/slug.md)` line (the `slug` link
  text). If that line is missing, the parent epic is `Unknown`.
- **Feature scope (one-line)**: extracted from the feature doc's `## What` section body (the text between
  the `## What` heading and the next `##` heading or EOF). Extraction rule: take the first sentence — text
  up to and including the first sentence-ending `.` that is followed by whitespace/newline/EOF, where a
  "sentence-ending" period excludes one preceded by a decimal digit (`v1.0`) or by a short lowercase
  abbreviation pattern (a single letter, dot, single letter — e.g. `e.g.`/`i.e.`) — trimmed of markdown bold
  markers (`**`) and collapsed whitespace/newlines to single spaces. If the extracted sentence would be
  empty (e.g. the section has only a heading, no body), that is the "malformed" case below.
- **Feature doc missing `## What`**: this is a hard error — the script raises `ValueError` with the offending
  file path in the message and exits non-zero. It never silently skips the feature or emits an empty-scope
  row.
- **ADR number**: parsed from the `# ADR-NNN: Title` H1 heading (or the filename `adr-NNN-...md` as a
  fallback if the heading doesn't match, to stay robust — but the heading is authoritative for the number
  used in comparisons/sorting since it's what a human reads).
- **ADR title**: the text after `ADR-NNN:` on the H1 heading line.
- **ADR status**: the first non-blank line after the `## Status` heading, read verbatim (e.g. `Accepted`,
  `Proposed`). Never read from the GitHub board/API — doc-static only.
- **ADR doc missing `# ADR-NNN: Title` heading or `## Status` section**: hard error (`ValueError`), same
  fail-loud contract as the missing feature `## What`.

### Empty directories

An initiative with an empty (or absent) `features/` or `adrs/` directory is valid — the corresponding
`INDEX.md` section is still emitted, with just a header row and no data rows (never an error, never an
omitted section).

### No network / no board calls

The generator does zero network calls (no `gh`, no HTTP). It walks only the local markdown tree under the
given `--initiative-path`. This makes it safe to run offline and in CI without a token.

## CLI

```
python3 scripts/generate_initiative_index.py --initiative-path <path-to-initiatives/slug>
```

- `--initiative-path` (required): path to `initiatives/<slug>/` (absolute or relative to CWD). Must contain
  an `epics/` directory at minimum (features/adrs dirs are optional — treated as empty if absent) or the
  script raises `ValueError` (not a valid initiative directory).
- Writes `<initiative-path>/INDEX.md`, overwriting any existing file.
- Exit code 0 on success; non-zero (via an uncaught exception, matching the sibling toolkit scripts'
  convention of no custom error-handling wrapper) on any malformed-doc error.

## Files

- `scripts/generate_initiative_index.py` (new) — the generator, stdlib-only (`re`, `pathlib`, `argparse`,
  `from __future__ import annotations`), following the style of `scripts/discover_engineering_work_candidates.py`.
- `tests/test_generate_initiative_index.py` (new) — pytest, function-based, using `tmp_path` fixtures to
  build small synthetic initiative trees (epics/features/adrs) rather than depending on the live
  `product-workspace` checkout.

## Verification

- `python3 -m pytest tests/test_generate_initiative_index.py -q`
- `python3 -m pytest tests/ -q` (full suite, no regressions)
- `python3 scripts/doctor.py --strict`
- Manual smoke: run against a real initiative directory (e.g.
  `~/projects/product-workspace/initiatives/subsurface-agentic-ai`) copied into a temp dir, confirm
  `INDEX.md` is produced and running the script twice produces a byte-identical file (`diff` returns
  no output).

## Edge Cases

- Feature doc missing `## What` -> `ValueError`, script exits non-zero, no partial `INDEX.md` written.
- ADR doc missing `## Status` or malformed H1 -> `ValueError`, same fail-loud contract.
- Empty `features/` or `adrs/` directory -> valid, empty section with header only.
- Missing `features/` or `adrs/` directory entirely (not just empty) -> treated the same as empty (no error).
- Epic doc missing `## Metadata`/`Phase` -> phase falls back to `Unknown`, not an error (phase is
  best-effort; only the two documented hard-error cases above should fail the run).
- Multiple ADRs / features/epics with the same slug (shouldn't happen, but) -> generator does not dedupe;
  each file is one row (duplicate detection is out of scope for this feature).
- `adr-list.md` (the catalog file, not a numbered ADR) is excluded from the ADR table by filename pattern
  (`adr-\d+-.*\.md`, not `adr-list.md`).
