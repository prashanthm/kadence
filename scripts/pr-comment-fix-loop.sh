#!/usr/bin/env bash
# Wrapper for local PR comment fix loop — invoke agent with prompt + config.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG="${PR_FIX_CONFIG:-$HOME/.config/ai-sdlc/pr-comment-fix-loop.yaml}"
PROMPT="$TOOLKIT_ROOT/.github/prompts/pr-comment-fix-loop.prompt.md"

if [[ ! -f "$PROMPT" ]]; then
  echo "error: missing prompt $PROMPT" >&2
  exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
  CONFIG="$TOOLKIT_ROOT/skills/pr-comment-fix-loop/config.example.yaml"
  echo "using example config: $CONFIG" >&2
fi

export PR_FIX_CONFIG="$CONFIG"
if [[ "${PR_FIX_REPORT_DRAFT:-}" == "1" ]]; then
  export PR_FIX_REPORT_DRAFT
fi

PROMPT_FOR_AGENT="$PROMPT"
if [[ -n "${PR_FIX_FORCE_PR:-}" ]]; then
  PROMPT_FOR_AGENT="$(mktemp "${TMPDIR:-/tmp}/pr-fix-prompt.XXXXXX")"
  trap 'rm -f "$PROMPT_FOR_AGENT"' EXIT
  {
    cat "$PROMPT"
    echo ""
    echo "## Pinned candidate (this firing only)"
    echo ""
    echo "Run discovery **only** with \`--force-pr ${PR_FIX_FORCE_PR}\`. Do not pick any other PR."
    echo ""
    echo '```bash'
    echo "python3 scripts/discover_pr_fix_candidates.py \\"
    echo "  --config \"\$PR_FIX_CONFIG\" --force-pr ${PR_FIX_FORCE_PR} --json"
    echo '```'
  } > "$PROMPT_FOR_AGENT"
fi

# Per-candidate clone path (set by cron for the selected PR's repo); falls back
# to git.primary_clone for manual runs and single-repo overlays.
if [[ -n "${PR_FIX_CLONE_PATH:-}" ]]; then
  WORKSPACE="$(python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from pr_fix_config import expand_path
print(expand_path('$PR_FIX_CLONE_PATH'))
")"
else
  WORKSPACE="$(python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from pr_fix_config import load_config, expand_path
cfg = load_config('$CONFIG')
print(expand_path(cfg.get('git', {}).get('primary_clone', '.')))
")"
fi

exec "$SCRIPT_DIR/invoke_loop_agent.sh" "$CONFIG" "$PROMPT_FOR_AGENT" "$WORKSPACE"
