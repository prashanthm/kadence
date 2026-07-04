#!/usr/bin/env bash
# Prepare (draft mode) or publish PR Comment Fix Report after operator review.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NS="${KADENCE_NAMESPACE:-kadence}"
CONFIG="${PR_FIX_CONFIG:-$HOME/.config/${NS}/pr-comment-fix-loop.yaml}"
MODE="auto"
PR_NUM=""
REPO="prashanthm/product-workspace"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --publish)
      MODE="publish"
      shift
      ;;
    *)
      if [[ -z "$PR_NUM" ]]; then
        PR_NUM="$1"
      else
        REPO="$1"
      fi
      shift
      ;;
  esac
done

[[ -n "$PR_NUM" ]] || {
  echo "usage: pr-comment-fix-loop-submit.sh <pr-number> [owner/repo]" >&2
  echo "       pr-comment-fix-loop-submit.sh --publish <pr-number> [owner/repo]" >&2
  exit 1
}

if [[ ! -f "$CONFIG" ]]; then
  CONFIG="$SCRIPT_DIR/../skills/pr-comment-fix-loop/config.example.yaml"
fi

python3 "$SCRIPT_DIR/pr_fix_submit.py" \
  --config "$CONFIG" \
  --repo "$REPO" \
  --pr "$PR_NUM" \
  --mode "$MODE"
