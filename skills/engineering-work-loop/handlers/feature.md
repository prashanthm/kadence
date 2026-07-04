# Handler — feature (loop mode)

Work item type: `feature`  
Branch: `feat/<issue#>-<slug>`

## When

Label `feature`; feature md linked; ≤ `max_auto_tasks` tasks; Loop AC with verify steps.

## Workflow

Delegate to [implement](../../implement/SKILL.md) with **loop mode**:

- All git operations in `$LOOP_CWD` worktree — not primary clone.
- Mark feature md AC `[x]` only when verified.
- `Refs #N` until all AC met; then `Closes #N`.
- Open PR with `gh pr create --draft` (loop mode only — not the default implement path).

## Skip

Depends On not satisfied; task count > max_auto_tasks; no verify commands on AC.
