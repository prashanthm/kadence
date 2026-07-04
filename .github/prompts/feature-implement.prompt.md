using the skill @sym:# Implement From Feature Skill

Implement the feature from its markdown file using the feature-direct build cycle (Tasks table + optional Implementation Plan; no GitHub task sub-issues).

**Feature:** <!-- REPLACE: path to feature md OR GitHub issue #, e.g. initiatives/ai-native-development/features/e07-f03-issue-hierarchy-migration.md or #105 -->

**Branch:** `feat/<issue#>-<slug>` — create from the base ref if missing (default `main`; the loop forks from `ENGINEERING_LOOP_BASE_REF`, e.g. the integration branch):

```bash
git fetch origin && git checkout main && git pull origin main
git checkout -b feat/<issue#>-<slug>
```

Follow the skill workflow: read AC and Tasks, draft Implementation Plan if needed, implement in Tasks order, update Tasks status and AC checkboxes in the same PR, run verification (Loop AC `verify:` commands / `verify_loop_ac.py`), then commit, push, and open PR. Use `Closes #<feature-issue>` only when all AC are checked. Status lives on the GitHub board, not in markdown — v2 has no `sync_status.py` / issue-sync step.
