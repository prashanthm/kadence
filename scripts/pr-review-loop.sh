#!/usr/bin/env bash
# Wrapper for the local PR review loop — invoke agent with prompt + config.
# A review firing posts a review (gh pr review); it does not edit code, so the
# workspace is just the operator's base clone (used for cross-file context and
# the optional read-only toolkit worktree).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NS="${KADENCE_NAMESPACE:-kadence}"
CONFIG="${PR_REVIEW_LOOP_CONFIG:-$HOME/.config/${NS}/pr-review-loop.yaml}"
PROMPT="$TOOLKIT_ROOT/.github/prompts/pr-review-loop.prompt.md"

# shellcheck source=loop_resolve_python.sh
source "$SCRIPT_DIR/loop_resolve_python.sh"
resolve_python

if [[ ! -f "$PROMPT" ]]; then
  echo "error: missing prompt $PROMPT" >&2
  exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
  CONFIG="$TOOLKIT_ROOT/skills/pr-review-loop/config.example.yaml"
  echo "using example config: $CONFIG" >&2
fi

export PR_REVIEW_LOOP_CONFIG="$CONFIG"

PROMPT_FOR_AGENT="$PROMPT"
if [[ -n "${PR_REVIEW_LOOP_FORCE_PR:-}" ]]; then
  PROMPT_FOR_AGENT="$(mktemp "${TMPDIR:-/tmp}/pr-review-prompt.XXXXXX")"
  trap 'rm -f "$PROMPT_FOR_AGENT"' EXIT
  {
    cat "$PROMPT"
    echo ""
    SCRIPT_DIR_PY="$SCRIPT_DIR" PR_REVIEW_LOOP_CONFIG="$CONFIG" \
      PR_REVIEW_LOOP_FORCE_PR="$PR_REVIEW_LOOP_FORCE_PR" \
      "${PYTHON_CMD[@]}" "$SCRIPT_DIR/pr_review_pinned_prompt.py"
  } > "$PROMPT_FOR_AGENT"
fi

WORKSPACE="$(SCRIPT_DIR_PY="$SCRIPT_DIR" CONFIG_PY="$CONFIG" "${PYTHON_CMD[@]}" -c "
import os, sys
sys.path.insert(0, os.environ['SCRIPT_DIR_PY'])
from pr_review_loop_config import load_config, expand_path
cfg = load_config(os.environ['CONFIG_PY'])
print(expand_path(cfg.get('git', {}).get('primary_clone', '.')))
")"

exec "$SCRIPT_DIR/invoke_loop_agent.sh" "$CONFIG" "$PROMPT_FOR_AGENT" "$WORKSPACE"
