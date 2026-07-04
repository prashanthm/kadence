# Contributing to the toolkit

The toolkit dogfoods its own process. Work on it the way it tells adopters to work.

## Branch model (during v2)

`main` is the released line. Active v2 work lands on the long-lived **`v2-integration`**
branch:

```
main  ──────────────────────────●   (release line)
        \                        ↑
         v2-integration  ●──●──●  └── one PR: v2-integration → main at release
            ↑    ↑
         feat/ feat/                  feature branches off v2-integration, PR'd into it
```

- Branch each change off `v2-integration` (`feat/<slug>`, `fix/<slug>`).
- PR into `v2-integration`, not `main`.
- Keep feature branches short; merge them in and delete them.
- Periodically merge `main → v2-integration` to absorb upstream (never the reverse).

## The gate

Every change must keep **`kadence doctor`** green — it runs the test suite, checks the loop
engine imports, validates skill-registry integrity (no dangling handler/skill links), and
round-trips the event log. CI runs it on every PR.

```
python3 scripts/doctor.py
```

Add a test for any new script behavior. The suite lives in `tests/` and doctor runs it.

## The rules the toolkit enforces on itself

- **Markdown holds durable intent; GitHub holds mutable state.** No `**Status:**` field, no
  dates, no positional IDs in docs. Slug-named.
- **The agent proposes; the deterministic harness disposes.** No green without a command the
  harness re-runs and an artifact it can see.
- **Stay lean.** This toolkit exists because Spec Kit was voluminous. Every addition should
  earn its place; prefer removing over adding. If a feature would re-introduce a sync, a
  status duplicate, or a compliance loop, it's the wrong feature.

## Naming

Identity is a descriptive slug, everywhere — never `eNN-fNN`. The join between a doc and its
GitHub issue is slug + branch + `Closes owner/repo#N`; the issue links out to the doc.
