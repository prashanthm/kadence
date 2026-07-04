#!/usr/bin/env bash
# Wrapper for local engineering work loop — invoke agent with prompt + config.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOOLKIT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck source=loop_resolve_python.sh
source "$SCRIPT_DIR/loop_resolve_python.sh"
resolve_python || exit 1

# Which family loop runs (implement-loop, spec-loop, pr-review-loop, pr-comment-fix-loop).
# The registry resolves the config-overlay stem and the default prompt; empty or the
# legacy family name resolves to implement-loop (backward compatible).
LOOP_NAME="${ENGINEERING_LOOP_NAME:-}"
CONFIG_STEM="$("${PYTHON_CMD[@]}" -c "
import sys; sys.path.insert(0, '$SCRIPT_DIR')
from loop_registry import resolve_loop_name
print(resolve_loop_name('$LOOP_NAME'))" 2>/dev/null || echo implement-loop)"
NS="${KADENCE_NAMESPACE:-kadence}"
CONFIG="${ENGINEERING_LOOP_CONFIG:-$HOME/.config/${NS}/${CONFIG_STEM}.yaml}"

# Prompt: ENGINEERING_LOOP_PROMPT (from the cron descriptor) wins; else the loop's
# default prompt. A bare filename resolves under .github/prompts/.
PROMPT="${ENGINEERING_LOOP_PROMPT:-}"
if [[ -z "$PROMPT" ]]; then
  PROMPT="$("${PYTHON_CMD[@]}" -c "
import sys; sys.path.insert(0, '$SCRIPT_DIR')
from loop_registry import get_loop
print(get_loop('$LOOP_NAME').prompt)" 2>/dev/null || echo implement-loop.prompt.md)"
fi
if [[ ! -f "$PROMPT" && -f "$TOOLKIT_ROOT/.github/prompts/$PROMPT" ]]; then
  PROMPT="$TOOLKIT_ROOT/.github/prompts/$PROMPT"
fi

if [[ ! -f "$PROMPT" ]]; then
  echo "error: missing prompt $PROMPT" >&2
  exit 1
fi

if [[ ! -f "$CONFIG" ]]; then
  CONFIG="$TOOLKIT_ROOT/skills/engineering-work-loop/config.example.yaml"
  echo "using example config: $CONFIG" >&2
fi

export ENGINEERING_LOOP_CONFIG="$CONFIG"

PROMPT_FOR_AGENT="$PROMPT"
if [[ -n "${ENGINEERING_LOOP_FORCE_ISSUE:-}" ]]; then
  PROMPT_FOR_AGENT="$(mktemp "${TMPDIR:-/tmp}/eng-loop-prompt.XXXXXX")"
  trap 'rm -f "$PROMPT_FOR_AGENT"' EXIT
  {
    cat "$PROMPT"
    echo ""
    echo "## Pinned candidate (this firing only)"
    echo ""
    echo "Discovery already selected this issue. Run discovery **only** with \`--force-issue ${ENGINEERING_LOOP_FORCE_ISSUE}\`. Do not pick any other item."
    echo ""
    echo '```bash'
    echo "python3 scripts/discover_engineering_work_candidates.py \\"
    echo "  --config \"\$ENGINEERING_LOOP_CONFIG\" --force-issue ${ENGINEERING_LOOP_FORCE_ISSUE} --json"
    echo '```'
  } > "$PROMPT_FOR_AGENT"
fi

# Per-candidate clone path (set by cron for the selected item); falls back to
# git.primary_clone for manual runs and single-repo overlays.
if [[ -n "${ENGINEERING_LOOP_CLONE_PATH:-}" ]]; then
  WORKSPACE="$(python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from engineering_work_loop_config import expand_path
print(expand_path('$ENGINEERING_LOOP_CLONE_PATH'))
")"
else
  WORKSPACE="$(python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from engineering_work_loop_config import load_config, expand_path
cfg = load_config('$CONFIG')
print(expand_path(cfg.get('git', {}).get('primary_clone', '.')))
")"
fi

exec "$SCRIPT_DIR/invoke_loop_agent.sh" "$CONFIG" "$PROMPT_FOR_AGENT" "$WORKSPACE"
