#!/usr/bin/env bash
# Acquire an isolated git worktree for the engineering work loop.
# Primary clone: git fetch only — never checkout/pull/merge here.
set -euo pipefail

usage() {
  echo "Usage: worktree_acquire.sh <primary-clone> <item-id> <branch-name> [base-ref]" >&2
  echo "  base-ref defaults to origin/main" >&2
  exit 1
}

assert_not_primary_cwd() {
  local primary="$1"
  if [[ "${LOOP_STRICT_PRIMARY:-1}" == "1" && "$(pwd -P)" == "$(cd "$primary" && pwd -P)" ]]; then
    echo "error: refusing git work in primary clone ($primary); use worktree path" >&2
    exit 1
  fi
}

[[ $# -ge 3 ]] || usage

PRIMARY_CLONE="$(cd "$1" && pwd)"
ITEM_ID="$2"
BRANCH="$3"
BASE_REF="${4:-origin/main}"
NS="${KADENCE_NAMESPACE:-kadence}"
WORKTREE_ROOT="${WORKTREE_ROOT:-$HOME/.local/share/${NS}/worktrees}"
REPO_SLUG="$(basename "$PRIMARY_CLONE")"
WT_PATH="$WORKTREE_ROOT/$REPO_SLUG/$ITEM_ID"

cd "$PRIMARY_CLONE"
export LOOP_PRIMARY_CLONE="$PRIMARY_CLONE"

git fetch origin

mkdir -p "$WORKTREE_ROOT/$REPO_SLUG"

if [[ -d "$WT_PATH" ]]; then
  echo "worktree exists: $WT_PATH" >&2
  cd "$WT_PATH"
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "error: worktree $WT_PATH has uncommitted changes; run worktree_release.sh --force or clean manually" >&2
    exit 1
  fi
  git checkout "$BRANCH"
else
  if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git worktree add "$WT_PATH" "$BRANCH"
  elif git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
    git worktree add -B "$BRANCH" "$WT_PATH" "origin/$BRANCH"
  else
    git worktree add -B "$BRANCH" "$WT_PATH" "$BASE_REF"
  fi
  cd "$WT_PATH"
fi

CURRENT="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$CURRENT" != "$BRANCH" ]]; then
  echo "error: expected branch $BRANCH but on $CURRENT" >&2
  exit 1
fi

if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  git pull --ff-only origin "$BRANCH"
elif [[ "$BASE_REF" == origin/* ]] && git show-ref --verify --quiet "refs/remotes/${BASE_REF}"; then
  git pull --ff-only origin "${BASE_REF#origin/}"
fi

assert_not_primary_cwd "$PRIMARY_CLONE"
echo "$WT_PATH"
