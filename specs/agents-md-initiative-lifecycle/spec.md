# Spec: agents-md-initiative-lifecycle

> Feature issue: [your-org/kadence#25](https://github.com/your-org/kadence/issues/25)
> Part of epic: [prashanthm/product-workspace#666](https://github.com/prashanthm/product-workspace/issues/666) (`planning-index-and-context-discovery`)

## Behavior

A standalone CLI script, `scripts/bootstrap_initiative_agents_md.py`, that `initiative-generation` runs as
its final required step for every *new* initiative. Given an initiative slug and the `product-workspace`
repo root, it:

1. **Creates `initiatives/<slug>/AGENTS.md`** — a minimal AGENTS.md-spec-conformant file for that
   initiative, seeded from that initiative's own `initiative.md` (Why/What), not blank scaffolding.
2. **Appends exactly one new row** to the root `AGENTS.md` routing table (the `| Initiative | Purpose |
   INDEX.md |` table under `## Routing table`), pointing at `initiatives/<slug>/INDEX.md`, without
   disturbing any existing row, heading, or surrounding prose byte-for-byte.

Both steps are idempotent: re-running against an initiative that already has an `AGENTS.md` and a routing
table row is a safe no-op for that initiative (see Idempotency below).

### Per-initiative `AGENTS.md` content

Seeded, not blank. Fields extracted from `initiatives/<slug>/initiative.md`:

- **Title**: `# AGENTS.md` (matches the convention already used at the product-workspace root; the initiative
  name appears in the intro sentence, not the H1, to match root style).
- **Intro sentence**: one sentence naming the initiative and summarizing its `## Why` (first sentence of the
  `## Why` section body, reusing the same first-sentence extraction heuristic as
  `generate_initiative_index.py`'s `extract_first_sentence`).
- **What this initiative delivers**: the `## What` section body copied verbatim (already-authored prose —
  no re-summarization) under a `## What this initiative delivers` heading.
- **Where things live**: a short fixed-shape section listing the standard initiative doc layout
  (`initiative.md`, `product-brief.md`, `epics/`, `features/`, `adrs/`, `INDEX.md`) relative to this
  directory, and a pointer to read the root `AGENTS.md` and this initiative's `INDEX.md` (when it exists)
  before drafting new content — consistent with the root file's "Read this first" doctrine.
- Missing `## Why` or `## What` in the source `initiative.md` is a hard error (`ValueError` naming the file)
  — an initiative charter without those sections is malformed, and silently emitting a stub AGENTS.md would
  reintroduce the "blank scaffolding" failure mode the epic is explicitly guarding against.

### Root `AGENTS.md` routing-table row

One new row appended as the **last** row of the existing routing table, in the same column order and
markdown-table-cell style as existing rows:

```
| [`<slug>`](initiatives/<slug>/initiative.md) | <intro sentence used in the AGENTS.md, same text> | [`initiatives/<slug>/INDEX.md`](initiatives/<slug>/INDEX.md) |
```

The insertion is done by locating the table's header/separator (`| Initiative | Purpose | INDEX.md |` /
`|---|---|---|`) and the contiguous block of `|`-prefixed rows that follows it, then inserting the new row
immediately after the last existing row and before the first non-table line (blank line / next heading).
Every other line in the file — including all existing rows, headings, and prose before/after the table — is
left byte-identical.

### Idempotency

- **`AGENTS.md`**: if `initiatives/<slug>/AGENTS.md` already exists, the script does not overwrite it by
  default — it reports the file as already present and skips the write. An explicit `--force` flag allows
  intentional regeneration (re-seeding after an `initiative.md` rewrite), which does overwrite.
- **Routing-table row**: if a row for `<slug>` (matched by the `[`<slug>`](initiatives/<slug>/...)` link
  target, not by exact row text) already exists anywhere in the table, no new row is appended — the script
  reports the row as already present. This is independent of the `AGENTS.md` file-exists check, so a
  partially-completed prior run (file written, table append failed/was interrupted) can be safely re-run to
  completion without duplicating the row.
- Running the full script twice back-to-back on the same initiative is therefore a no-op on the second run
  (exit code 0, no file changes), matching the feature's AC-5.

### No network / no board calls

Pure filesystem operation — reads/writes only local markdown under the given `product-workspace` root path.
No `gh`, no HTTP.

## CLI

```
python3 scripts/bootstrap_initiative_agents_md.py \
  --product-workspace-root <path-to-product-workspace> \
  --initiative-slug <slug> \
  [--force]
```

- `--product-workspace-root` (required): path to the `product-workspace` repo root (contains root
  `AGENTS.md` and `initiatives/`).
- `--initiative-slug` (required): the initiative directory name under `initiatives/`. Must already exist and
  contain an `initiative.md` (raises `ValueError` if not — this script wires an *existing* initiative
  charter, it does not create one; `initiative-generation` calls it after the charter is written).
- `--force` (optional flag): overwrite an existing `initiatives/<slug>/AGENTS.md` with freshly-seeded
  content. Does not affect routing-table idempotency (the row check is always duplicate-safe regardless of
  `--force`).
- Exit code 0 on success (including the idempotent no-op case); non-zero via an uncaught exception on any
  malformed-input error, matching sibling toolkit scripts' convention.
- Prints a one-line summary to stdout for each of the two actions (created / already-present / overwritten
  for the AGENTS.md; row-appended / row-already-present for the routing table) so a caller (human or the
  `initiative-generation` skill run) can confirm what happened.

## Files

- `scripts/bootstrap_initiative_agents_md.py` (new) — the generator, stdlib-only (`re`, `pathlib`,
  `argparse`, `from __future__ import annotations`), following the style of
  `scripts/generate_initiative_index.py` (reuses its `extract_first_sentence`/`_section_body` pattern rather
  than duplicating the regex, since both scripts read the same markdown section-body shape).
- `tests/test_bootstrap_initiative_agents_md.py` (new) — pytest, function-based, using `tmp_path` fixtures to
  build a synthetic `product-workspace`-shaped tree (root `AGENTS.md` with a routing table,
  `initiatives/<slug>/initiative.md`) rather than depending on the live `product-workspace` checkout.
- `skills/initiative-generation/SKILL.md` (edit) — adds a required workflow step invoking this script after
  the charter is written and reviewed, and a Verification checklist item.

## Verification

- `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -q`
- `python3 -m pytest tests/ -q` (full suite, no regressions)
- `python3 scripts/doctor.py --strict`
- Manual smoke against the real `product-workspace` checkout: create a throwaway test initiative
  (`initiatives/zzz-test-lifecycle-verification/initiative.md`), run the script, diff the root `AGENTS.md`
  routing table before/after (exactly one row added, all other lines unchanged), confirm the new
  initiative's `AGENTS.md` is seeded (not blank), re-run the script a second time and confirm no duplicate
  row / no change on the second run, then delete the throwaway initiative directory and revert the root
  `AGENTS.md` to its pre-test state (this is a scratch verification against a repo this feature does not
  otherwise modify — `product-workspace` must show a clean `git status` afterward).

## Edge Cases

- `initiatives/<slug>/initiative.md` missing entirely -> `ValueError` (this script wires an existing
  charter; it is not `initiative-generation`'s charter-authoring step).
- `initiative.md` missing `## Why` or `## What` -> `ValueError` naming the file (malformed charter; refuses
  to emit blank-scaffolding AGENTS.md content).
- `initiatives/<slug>/AGENTS.md` already exists, no `--force` -> no-op for that step, reported, exit 0.
- `initiatives/<slug>/AGENTS.md` already exists, `--force` given -> overwritten with freshly-seeded content.
- A row for `<slug>` already exists in the routing table -> no-op for that step (regardless of `--force`),
  reported, exit 0.
- Root `AGENTS.md` missing entirely, or missing the `## Routing table` heading / table -> `ValueError` (the
  bootstrap dependency — `agents-md-bootstrap` — is expected to have already created this; this script
  does not create the routing table from scratch).
- `initiatives/<slug>/` missing entirely -> `ValueError` (same as the `initiative.md`-missing case; the
  script never creates the initiative directory itself).
