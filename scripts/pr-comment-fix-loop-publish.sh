#!/usr/bin/env bash
# Human gate — run generated publish script after reviewing draft + diff.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NS="${KADENCE_NAMESPACE:-kadence}"
CONFIG="${PR_FIX_CONFIG:-$HOME/.config/${NS}/pr-comment-fix-loop.yaml}"
PR_NUM="${1:?usage: pr-comment-fix-loop-publish.sh <pr-number> [owner/repo]}"
REPO="${2:-prashanthm/product-workspace}"

if [[ "${PR_FIX_PUBLISH:-}" != "1" ]]; then
  echo "error: set PR_FIX_PUBLISH=1 after reviewing the generated publish script" >&2
  echo "  1. scripts/pr-comment-fix-loop-submit.sh $PR_NUM" >&2
  echo "  2. review ~/.local/share/${NS}/pr-fix-reports/${REPO#*/}-${PR_NUM}-publish.sh" >&2
  echo "  3. PR_FIX_PUBLISH=1 scripts/pr-comment-fix-loop-publish.sh $PR_NUM" >&2
  exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
  CONFIG="$SCRIPT_DIR/../skills/pr-comment-fix-loop/config.example.yaml"
fi

python3 "$SCRIPT_DIR/pr_fix_submit.py" \
  --config "$CONFIG" \
  --repo "$REPO" \
  --pr "$PR_NUM" \
  --mode publish
