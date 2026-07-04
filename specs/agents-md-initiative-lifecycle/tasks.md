# Tasks: agents-md-initiative-lifecycle

## Task 1 — AGENTS.md content builder

Implement `build_initiative_agents_md`, `extract_purpose_sentence` in
`scripts/bootstrap_initiative_agents_md.py`, importing `extract_first_sentence`/`_section_body` from
`generate_initiative_index`.

### Loop AC

- [x] AC-1: `build_initiative_agents_md` raises `ValueError` naming the initiative slug when the source
  `initiative.md` text has no `## Why` section or an empty one.
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k missing_why -q`
- [x] AC-2: `build_initiative_agents_md` raises `ValueError` when `## What` is missing or empty.
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k missing_what -q`
- [x] AC-3: Given a well-formed `initiative.md`, `build_initiative_agents_md` returns content containing the
  initiative slug, a `## What this initiative delivers` section whose body matches the source `## What`
  section verbatim, and a `## Where things live` section — i.e. seeded from real charter content, not blank
  scaffolding.
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k seeded_content -q`
- [x] AC-4: `extract_purpose_sentence` returns the same first-sentence text used inside the built AGENTS.md's
  intro, so the routing-table row and the AGENTS.md intro never drift from each other.
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k purpose_sentence_matches -q`

## Task 2 — Routing-table row insertion

Implement `insert_routing_row` in `scripts/bootstrap_initiative_agents_md.py`.

### Loop AC

- [x] AC-1: Given a root `AGENTS.md` text with an existing routing table of N rows, `insert_routing_row`
  for a new slug returns text with exactly N+1 rows, the new row last, and every other line byte-identical
  to the input.
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k insert_new_row -q`
- [x] AC-2: Given a root `AGENTS.md` text whose table already has a row for `slug`, `insert_routing_row`
  returns `(text, False)` with `text` identical to the input (no duplicate row).
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k insert_existing_row -q`
- [x] AC-3: `insert_routing_row` raises `ValueError` when the routing table header/separator cannot be found
  in the input text.
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k missing_table -q`

## Task 3 — Orchestration, idempotency, and CLI

Implement `bootstrap_initiative_agents_md` and the `argparse` `main()` wrapper.

### Loop AC

- [x] AC-1: Given a synthetic `product-workspace`-shaped `tmp_path` tree (root `AGENTS.md` with a routing
  table, `initiatives/<slug>/initiative.md`), a first run of `bootstrap_initiative_agents_md` writes
  `initiatives/<slug>/AGENTS.md` and appends one routing row, returning
  `{"agents_md": "created", "routing_row": "appended"}`.
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k first_run_creates -q`
- [x] AC-2: A second run against the same tree (no `--force`) makes no filesystem changes and returns
  `{"agents_md": "skipped", "routing_row": "skipped"}` — idempotent re-run, satisfying AC-5 of the feature.
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k second_run_idempotent -q`
- [x] AC-3: A run with `force=True` against an existing `AGENTS.md` overwrites it (`"overwritten"`) while the
  routing-row step remains `"skipped"` if the row already exists (the two idempotency checks are
  independent).
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k force_overwrite -q`
- [x] AC-4: The CLI runs end-to-end: `python3 scripts/bootstrap_initiative_agents_md.py
  --product-workspace-root <dir> --initiative-slug <slug>` performs the same effects as the direct function
  call and exits 0.
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k cli -q`
- [x] AC-5: Missing `initiative.md`, missing initiative directory, or missing root `AGENTS.md`/routing table
  each raise `ValueError` with no partial writes.
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -k missing_input -q`

## Task 4 — Skill-doc wiring

Edit `skills/initiative-generation/SKILL.md`: add a required workflow step invoking
`scripts/bootstrap_initiative_agents_md.py` after the charter file is written, and a matching Verification
checklist item.

### Loop AC

- [x] AC-1: `SKILL.md`'s Required Workflow numbered list includes a step naming
  `scripts/bootstrap_initiative_agents_md.py` and explicitly labeling it "Required" (not phrased as
  discretionary/skippable).
  - verify: `grep -B3 "bootstrap_initiative_agents_md.py" skills/initiative-generation/SKILL.md | grep -qi "required"`
- [x] AC-2: `SKILL.md`'s Verification checklist includes a line confirming the initiative's `AGENTS.md` was
  created/updated and the root routing table row was appended.
  - verify: `grep -qE "AGENTS\.md" skills/initiative-generation/SKILL.md && grep -qE "routing" skills/initiative-generation/SKILL.md`

## Task 5 — Full verification pass

- [x] AC-1: New test file passes standalone.
  - verify: `python3 -m pytest tests/test_bootstrap_initiative_agents_md.py -q`
- [x] AC-2: Full suite has no regressions.
  - verify: `python3 -m pytest tests/ -q`
- [x] AC-3: `doctor.py --strict` passes.
  - verify: `python3 scripts/doctor.py --strict`
- [x] AC-4: Manual throwaway-initiative smoke test against the real `product-workspace` checkout: create
  `initiatives/zzz-test-lifecycle-verification/initiative.md`, run the CLI, diff the root `AGENTS.md`
  routing table before/after (exactly one row added), confirm the new `AGENTS.md` is seeded, re-run and
  confirm idempotency (no diff on second run), then delete the throwaway initiative and revert
  `product-workspace/AGENTS.md` to its pre-test state (`git status` clean afterward — this is scratch
  verification, not a committed change to `product-workspace`).
  - verify: manual (see spec.md Verification); not a pytest target since it touches a sibling repo outside
    `kadence`.
