# GitHub issue — Loop AC block

Add this section to any issue eligible for the engineering work loop. The issue is joined to its doc by slug + branch and links back to it; work lands via `Closes owner/repo#N` on the PR.

## Loop AC

**Work item type:** chore
**Risk tier:** auto

- [ ] AC-1: Describe observable outcome
  - verify: `test -f path/to/expected/file`
- [ ] AC-2: The behavior works (tests pass)
  - verify: `python3 scripts/loop_check.py cmd-succeeds "pytest tests/test_feature.py -q"`

Rules:

- Loop AC verify **behavior only** — tests pass, files exist, lint clean. There is no diff-size gate; the feature was already right-sized at generation time.
- Each item must be pass/fail with an optional `verify:` command (required for `auto` tier).
- **Auto tier:** verify commands must be a single argv-style command — **no** pipes (`|`), redirects (`<`/`>`), `$`, backticks, `;`, or `&&`. For compound checks (file counts, status lookups), call `scripts/loop_check.py` instead of a shell pipeline. `assist`/`human-only` tiers may use shell.
- Agent checks `[x]` only after verify exits 0.
- PR must include Loop AC Evidence table.
