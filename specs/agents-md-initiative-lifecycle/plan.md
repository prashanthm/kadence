# Plan: agents-md-initiative-lifecycle

## Approach

Single-file stdlib script, mirroring `generate_initiative_index.py` conventions (module docstring,
`from __future__ import annotations`, small pure functions composed by an orchestrating function, thin
`argparse` CLI wrapper). Reuses `generate_initiative_index.extract_first_sentence` and
`generate_initiative_index._section_body` by importing them directly (same package/dir, same import style
already used by other toolkit scripts, e.g. `discover_engineering_work_candidates.py` importing
`classify_work_item`) rather than re-implementing the same regex logic a second time.

Two independent, separately-idempotent sub-operations, each pure-function-testable without touching the
filesystem in the unit-test core (a thin I/O wrapper does the actual read/write, matching
`generate_initiative_index.py`'s `generate_index()` shape):

1. `build_initiative_agents_md(initiative_md_text: str, slug: str) -> str` — pure function, given the text of
   `initiative.md` and the slug, returns the full `AGENTS.md` content string. Raises `ValueError` if `## Why`
   or `## What` is missing/empty.
2. `insert_routing_row(root_agents_md_text: str, slug: str, purpose: str) -> tuple[str, bool]` — pure
   function, given the current root `AGENTS.md` text, returns `(new_text, was_inserted)`. `was_inserted` is
   `False` (text unchanged) if a row for `slug` already exists; otherwise the row is appended after the last
   existing table row and `new_text` differs only by that one inserted line.

Orchestration (`bootstrap_initiative_agents_md(product_workspace_root, slug, force=False) -> dict`) does the
file I/O: read `initiative.md`, call (1), check `AGENTS.md` existence for idempotency, write; read root
`AGENTS.md`, call (2), write only if changed. Returns a small status dict (`agents_md: created|skipped|
overwritten`, `routing_row: appended|skipped`) that both the CLI's printed summary and tests assert against.

## Files

- `scripts/bootstrap_initiative_agents_md.py` (new)
- `tests/test_bootstrap_initiative_agents_md.py` (new)
- `skills/initiative-generation/SKILL.md` (edit)

## Steps

1. **Charter parsing / AGENTS.md content builder**:
   - Import `extract_first_sentence` and `_section_body` from `generate_initiative_index`.
   - `build_initiative_agents_md(initiative_md_text: str, slug: str) -> str` — extracts `## Why` and
     `## What` bodies via `_section_body`; raises `ValueError` (naming that the source is `initiative.md` for
     `<slug>`) if either is missing/empty. Builds the intro sentence via `extract_first_sentence` on the
     `## Why` body. Renders the fixed-shape AGENTS.md: title, intro sentence, `## What this initiative
     delivers` (verbatim `## What` body), `## Where things live` (fixed doc-layout list + pointer to root
     AGENTS.md and this initiative's `INDEX.md`).
   - Also exposes `extract_purpose_sentence(initiative_md_text: str) -> str` (thin wrapper around the same
     `## Why` first-sentence extraction) so the routing-table row step reuses the *exact same* sentence
     without re-deriving it — this is what AC-1's "seeded from the initiative's own charter" and the routing
     row's one-line purpose share as a single source of truth.

2. **Routing-table row insertion**:
   - `insert_routing_row(root_agents_md_text: str, slug: str, purpose: str) -> tuple[str, bool]` — locates
     the routing table via a regex anchored on the header row `| Initiative | Purpose | INDEX.md |` followed
     by the separator row, then the contiguous run of `|`-prefixed lines. Checks each existing row's first
     cell link target (`initiatives/<row-slug>/initiative.md`) for a match on `slug`; if found, returns
     `(text, False)` unchanged. Otherwise builds the new row string
     (`| [`slug`](initiatives/slug/initiative.md) | purpose | [`initiatives/slug/INDEX.md`](initiatives/slug/INDEX.md) |`)
     and splices it in immediately after the last matched row line, preserving every other line verbatim
     (line-based splice, not a full-file regex substitution, to guarantee byte-identical untouched lines).
   - Raises `ValueError` if the routing table (header + separator) cannot be found at all — this signals the
     root `AGENTS.md` is missing the bootstrap this feature depends on.

3. **Orchestration + file I/O + idempotency**:
   - `bootstrap_initiative_agents_md(product_workspace_root: Path, slug: str, force: bool = False) -> dict`:
     - Validate `initiatives/<slug>/initiative.md` exists (else `ValueError`).
     - Read it, call `build_initiative_agents_md` and `extract_purpose_sentence`.
     - `initiatives/<slug>/AGENTS.md`: if absent, write, status `created`; if present and not `force`, status
       `skipped`; if present and `force`, overwrite, status `overwritten`.
     - Validate root `AGENTS.md` exists (else `ValueError`).
     - Read it, call `insert_routing_row`; if `was_inserted`, write back, status `appended`; else status
       `skipped`.
     - Return `{"agents_md": <status>, "routing_row": <status>}`.

4. **CLI**: `argparse` with `--product-workspace-root` (required), `--initiative-slug` (required), `--force`
   (flag), calls the orchestrator and prints the two status lines.

5. **Skill-doc edit**: add a numbered required step to `initiative-generation/SKILL.md`'s "Required Workflow"
   (after the charter is drafted and written, before/alongside "Present the draft for review" — the script
   only makes sense to run once the charter file exists on disk) invoking
   `scripts/bootstrap_initiative_agents_md.py`, plus a Verification checklist line. Framed as required
   (no "optional"/"consider" language), matching how `planning-skills-index-lookup` phrased its required
   INDEX.md-read step in sibling skills.

## ADRs

None — this feature has no ADR dependency (confirmed in the feature doc: "this is a skill-workflow wiring
capability... No ADR blocks or is produced by this feature").

## Edge Cases (see spec.md for full list)

- Missing `## Why`/`## What` in `initiative.md` -> `ValueError`, no partial write.
- `AGENTS.md` already exists (no `--force`) -> skip, not overwritten, exit 0.
- Routing row already present for slug -> skip, exit 0 (independent of `--force`).
- Root `AGENTS.md` missing or missing the routing table -> `ValueError` (bootstrap dependency not met).
- Two-invocation idempotency: same slug run twice -> second run is a full no-op (both statuses `skipped`).

## Verification

- `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -q`
- `python3 -m pytest tests/ -q`
- `python3 scripts/doctor.py --strict`
- Manual throwaway-initiative smoke test against the real `product-workspace` checkout (see spec.md
  Verification) — the AC-4/AC-5 concrete verification, done and reverted, not committed.
