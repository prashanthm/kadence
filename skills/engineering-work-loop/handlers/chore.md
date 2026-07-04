# Handler — chore

Work item type: `chore`  
Branch: `chore/<issue#>-<slug>`

## When

Label `chore` or title prefix `chore:`; body contains `## Loop AC` with verify commands.

## Auto tier

- All paths under config `chore.path_allowlist`
- ≤3 files changed
- All Loop AC verify commands pass

## Steps

1. Read closeout / issue description and Loop AC.
2. Implement minimal change in worktree.
3. Run each `verify:` command.
4. Open **draft** PR with Work Fix Report (`gh pr create --draft`). Do not request reviewers.
