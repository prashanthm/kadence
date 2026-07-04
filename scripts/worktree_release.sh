#!/usr/bin/env bash
# Release a loop worktree after PR opened or skip.
set -euo pipefail

usage() {
  echo "Usage: worktree_release.sh <primary-clone> <item-id> [--force]" >&2
  exit 1
}

[[ $# -ge 2 ]] || usage

PRIMARY_CLONE="$(cd "$1" && pwd)"
ITEM_ID="$2"
FORCE="${3:-}"
NS="${KADENCE_NAMESPACE:-kadence}"
WORKTREE_ROOT="${WORKTREE_ROOT:-$HOME/.local/share/${NS}/worktrees}"
REPO_SLUG="$(basename "$PRIMARY_CLONE")"
WT_PATH="$WORKTREE_ROOT/$REPO_SLUG/$ITEM_ID"

if [[ -n "$FORCE" && "$FORCE" != "--force" ]]; then
  usage
fi

cd "$PRIMARY_CLONE"

if [[ ! -d "$WT_PATH" ]]; then
  echo "no worktree at $WT_PATH" >&2
  exit 0
fi

if [[ -n "$(git -C "$WT_PATH" status --porcelain 2>/dev/null)" && "$FORCE" != "--force" ]]; then
  echo "worktree dirty; keeping $WT_PATH (use --force to remove)" >&2
  exit 1
fi

if [[ "$FORCE" == "--force" ]]; then
  git worktree remove "$WT_PATH" --force
else
  git worktree remove "$WT_PATH"
fi
git worktree prune

echo "released $WT_PATH" >&2
